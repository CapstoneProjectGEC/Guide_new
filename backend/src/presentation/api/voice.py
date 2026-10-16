"""Public voice REST and SSE streaming endpoints for speech transcription and voice interaction."""

import json
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.application.chat.conversation_manager import ConversationManager
from backend.src.application.voice.stt_service import SpeechToTextService
from backend.src.application.voice.tts_service import TextToSpeechService, get_tts_service
from backend.src.core.errors import AudioValidationError
from backend.src.core.logging import get_logger
from backend.src.domain.conversation import ChatMessageResponse, SendMessageRequest
from backend.src.domain.voice import (
    SynthesisRequest,
    TTSEngineStatus,
    TTSVoiceInfo,
    TranscriptionResult,
    VoiceChatResponse,
    VoiceEngineInfo,
)
from backend.src.infrastructure.audio.whisper_engine import get_whisper_engine
from backend.src.infrastructure.database.session import get_db_session

logger = get_logger("presentation.api.voice")
router = APIRouter(prefix="/voice", tags=["Tourist Voice"])


def get_stt_service() -> SpeechToTextService:
    """Dependency provider for SpeechToTextService."""
    return SpeechToTextService(whisper_engine=get_whisper_engine())


@router.get("/info", response_model=VoiceEngineInfo, status_code=status.HTTP_200_OK)
async def get_voice_info(
    stt_service: SpeechToTextService = Depends(get_stt_service),
) -> VoiceEngineInfo:
    """Retrieve speech recognition engine hardware, model, and configuration properties."""
    return stt_service.whisper_engine.get_info()


@router.post("/transcribe", response_model=TranscriptionResult, status_code=status.HTTP_200_OK)
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Spoken audio file (WebM, WAV, MP3, OGG, M4A)"),
    language: str | None = Form(None, description="Optional ISO language code hint ('kn' or 'en')"),
    stt_service: SpeechToTextService = Depends(get_stt_service),
) -> TranscriptionResult:
    """Transcribe spoken tourist audio into text using local faster-whisper (Zero auth required)."""
    raw_bytes = await audio_file.read()
    if not raw_bytes:
        raise AudioValidationError("Uploaded audio payload is empty.")

    return await stt_service.transcribe_audio_bytes(
        audio_bytes=raw_bytes,
        filename=audio_file.filename,
        content_type=audio_file.content_type,
        language=language,
    )


@router.post("/chat", response_model=VoiceChatResponse, status_code=status.HTTP_200_OK)
async def voice_chat(
    audio_file: UploadFile = File(..., description="Spoken voice question"),
    session_id: str | None = Form(None, description="Optional active session identifier"),
    client_fingerprint: str | None = Form(None, description="Optional tourist client fingerprint"),
    preferred_language: str | None = Form(None, description="Language preference override ('kn' or 'en')"),
    stt_service: SpeechToTextService = Depends(get_stt_service),
    db_session: AsyncSession = Depends(get_db_session),
) -> VoiceChatResponse:
    """End-to-end voice query endpoint: transcribes audio and executes grounded conversational RAG."""
    raw_bytes = await audio_file.read()
    if not raw_bytes:
        raise AudioValidationError("Uploaded audio payload is empty.")

    # 1. Transcribe speech
    transcription = await stt_service.transcribe_audio_bytes(
        audio_bytes=raw_bytes,
        filename=audio_file.filename,
        content_type=audio_file.content_type,
        language=preferred_language,
    )

    manager = ConversationManager(session=db_session)

    # 2. Check for silence or empty transcript
    if transcription.is_silent or not transcription.text.strip():
        lang = preferred_language or transcription.detected_language or "kn"
        fallback_silence = (
            "ಧ್ವನಿ ಪತ್ತೆಯಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ."
            if lang == "kn"
            else "No speech detected in audio. Please speak clearly into the microphone."
        )

        chat_session = await manager.get_or_create_session(
            session_id=session_id,
            client_fingerprint=client_fingerprint,
            preferred_language=lang,
        )

        return VoiceChatResponse(
            transcription=transcription,
            chat_response=ChatMessageResponse(
                id=f"silent_{chat_session.id[:8]}",
                session_id=chat_session.id,
                role="assistant",
                content=fallback_silence,
                detected_language=lang,
                input_mode="voice",
                latency_ms=transcription.latency_ms,
                is_grounded=False,
                created_at="just_now",
                citations=[],
            ),
        )

    # 3. Forward transcript to conversational RAG engine with voice input modality
    send_req = SendMessageRequest(
        session_id=session_id,
        client_fingerprint=client_fingerprint,
        content=transcription.text,
        preferred_language=preferred_language or transcription.detected_language,
        input_mode="voice",
    )

    chat_resp = await manager.process_message(send_req)

    return VoiceChatResponse(
        transcription=transcription,
        chat_response=chat_resp,
    )


@router.post("/stream")
async def voice_chat_stream(
    audio_file: UploadFile = File(..., description="Spoken voice query to transcribe and stream"),
    session_id: str | None = Form(None, description="Optional active session ID"),
    client_fingerprint: str | None = Form(None, description="Optional client fingerprint"),
    preferred_language: str | None = Form(None, description="Optional language preference override"),
    stt_service: SpeechToTextService = Depends(get_stt_service),
    db_session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Stream speech transcription event followed by token-by-token grounded RAG SSE answer."""
    raw_bytes = await audio_file.read()
    if not raw_bytes:
        raise AudioValidationError("Uploaded audio payload is empty.")

    async def stream_generator() -> AsyncGenerator[str, None]:
        # 1. Transcribe speech
        transcription = await stt_service.transcribe_audio_bytes(
            audio_bytes=raw_bytes,
            filename=audio_file.filename,
            content_type=audio_file.content_type,
            language=preferred_language,
        )

        # 2. Emit initial transcript event
        transcript_payload = {
            "text": transcription.text,
            "detected_language": transcription.detected_language,
            "language_probability": transcription.language_probability,
            "duration_seconds": transcription.duration_seconds,
            "is_silent": transcription.is_silent,
            "latency_ms": transcription.latency_ms,
        }
        yield f"event: transcript\ndata: {json.dumps(transcript_payload, ensure_ascii=False)}\n\n"

        manager = ConversationManager(session=db_session)

        # 3. Check for silence
        if transcription.is_silent or not transcription.text.strip():
            lang = preferred_language or transcription.detected_language or "kn"
            fallback_silence = (
                "ಧ್ವನಿ ಪತ್ತೆಯಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ."
                if lang == "kn"
                else "No speech detected in audio. Please speak clearly into the microphone."
            )
            chat_session = await manager.get_or_create_session(
                session_id=session_id,
                client_fingerprint=client_fingerprint,
                preferred_language=lang,
            )
            yield f"event: citations\ndata: {json.dumps({'citations': []}, ensure_ascii=False)}\n\n"
            for word in fallback_silence.split():
                yield f"event: token\ndata: {json.dumps({'token': word + ' '}, ensure_ascii=False)}\n\n"
            done_payload = {
                "message_id": f"silent_{chat_session.id[:8]}",
                "session_id": chat_session.id,
                "is_grounded": False,
                "detected_language": lang,
                "latency_ms": transcription.latency_ms,
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
            return

        # 4. Stream full RAG response
        send_req = SendMessageRequest(
            session_id=session_id,
            client_fingerprint=client_fingerprint,
            content=transcription.text,
            preferred_language=preferred_language or transcription.detected_language,
            input_mode="voice",
        )

        async for chunk in manager.process_message_stream(send_req):
            yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Phase 12: Offline Text-To-Speech (TTS) Endpoints
# ---------------------------------------------------------------------------


@router.post("/synthesize", status_code=status.HTTP_200_OK)
async def synthesize_speech(
    request: SynthesisRequest,
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> Response:
    """Synthesize text into offline WAV speech audio using local Piper neural voice models (Zero auth required)."""
    audio_bytes, metadata = await tts_service.synthesize(request)

    headers = {
        "Content-Disposition": 'inline; filename="synthesized_speech.wav"',
        "X-TTS-Engine": metadata.engine,
        "X-TTS-Language": metadata.language,
        "X-TTS-Voice": metadata.voice,
        "X-TTS-Latency-Ms": str(metadata.latency_ms),
        "X-TTS-Audio-Duration": str(metadata.duration_seconds),
        "X-TTS-Cached": "true" if metadata.cached else "false",
        "X-TTS-Fallback-Recommended": "true" if metadata.client_fallback_recommended else "false",
    }

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers=headers,
    )


@router.get("/tts/status", response_model=TTSEngineStatus, status_code=status.HTTP_200_OK)
async def get_tts_status(
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> TTSEngineStatus:
    """Retrieve speech synthesis status, operational state, registered voices, and LRU cache statistics."""
    return tts_service.get_status()


@router.get("/tts/voices", response_model=list[TTSVoiceInfo], status_code=status.HTTP_200_OK)
async def list_tts_voices(
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> list[TTSVoiceInfo]:
    """Retrieve list of recognized voice models and local disk availability."""
    return tts_service.get_available_voices()


@router.post("/tts/sync", status_code=status.HTTP_200_OK)
async def sync_voice_registry(
    tts_service: TextToSpeechService = Depends(get_tts_service),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Synchronize registered and discovered voice models with MySQL voice_registry table."""
    records = await tts_service.sync_voice_registry(session=db_session)
    await db_session.commit()
    return {
        "status": "success",
        "synced_voices_count": len(records),
        "voices": [
            {
                "voice_id": r.voice_id,
                "language_code": r.language_code,
                "engine": r.engine,
                "is_active": r.is_active,
            }
            for r in records
        ],
    }

