"""Controlled benchmark script to measure voice & chat stages post-repair."""

import asyncio
import io
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, r"d:\vikasAn")
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.src.application.chat.conversation_manager import ConversationManager
from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.application.chat.prompt_builder import PromptBuilder
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.application.voice.stt_service import SpeechToTextService
from backend.src.application.voice.tts_service import get_tts_service
from backend.src.domain.conversation import SendMessageRequest
from backend.src.domain.voice import SynthesisRequest
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.llm.ollama_client import get_ollama_client

TEST_QUERIES = [
    {
        "id": "Q1_FACTUAL_EN",
        "category": "factual",
        "lang": "en",
        "text": "Who commissioned the Chennakeshava Temple at Belur?",
    },
    {
        "id": "Q2_FACTUAL_KN",
        "category": "factual",
        "lang": "kn",
        "text": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
    },
    {
        "id": "Q3_RETRIEVAL_EN",
        "category": "retrieval",
        "lang": "en",
        "text": "What material was used to construct the Hoysala temple in Belur?",
    },
    {
        "id": "Q4_RETRIEVAL_KN",
        "category": "retrieval",
        "lang": "kn",
        "text": "ದೇವಾಲಯವನ್ನು ಯಾವ ಕಲ್ಲಿನಿಂದ ಕಟ್ಟಲಾಗಿದೆ?",
    },
    {
        "id": "Q5_TECHNICAL_EN",
        "category": "technical",
        "lang": "en",
        "text": "How many Madanika bracket figures are adorning the exterior pillars?",
    },
    {
        "id": "Q6_TECHNICAL_KN",
        "category": "technical",
        "lang": "kn",
        "text": "ಮದನಿಕಾ ಅಥವಾ ಶಿಲಾಬಾಲಿಕೆಯರ ಒಟ್ಟು ಸಂಖ್ಯೆ ಎಷ್ಟು?",
    },
    {
        "id": "Q7_MIXED_LANG",
        "category": "code-switch",
        "lang": "kn",
        "text": "Belur temple ನಲ್ಲಿ ಎಷ್ಟು Madanika figures ಇವೆ?",
    },
    {
        "id": "Q8_OOD_EN",
        "category": "out_of_domain",
        "lang": "en",
        "text": "What is the capital city of France?",
    },
    {
        "id": "Q9_OOD_KN",
        "category": "out_of_domain",
        "lang": "kn",
        "text": "ಫ್ರಾನ್ಸ್ ದೇಶದ ರಾಜಧಾನಿ ಯಾವುದು?",
    },
]

AUDIO_FIXTURES = [
    ("AUDIO_EN", Path("tests/fixtures/audio/english_query.wav"), "en"),
    ("AUDIO_KN", Path("tests/fixtures/audio/kannada_query.wav"), "kn"),
    ("AUDIO_MIXED", Path("tests/fixtures/audio/mixed_query.wav"), "kn"),
    ("AUDIO_SILENCE", Path("tests/fixtures/audio/silence.wav"), "en"),
]


async def run_benchmark():
    session_factory = get_session_factory()
    stt = SpeechToTextService()
    tts = get_tts_service()
    results = {"text_queries": [], "audio_queries": []}

    print("=" * 80)
    print("RUNNING CONTROLLED POST-REPAIR BENCHMARK")
    print("=" * 80)

    # 1. Benchmark Audio Ingestion / STT
    print("\n--- STAGE 1: SPEECH-TO-TEXT (STT) BENCHMARK ---")
    for audio_id, file_path, expected_lang in AUDIO_FIXTURES:
        if not file_path.exists():
            print(f"Skipping {audio_id}: File {file_path} not found.")
            continue
        audio_bytes = file_path.read_bytes()
        t0 = time.perf_counter()
        stt_result = await stt.transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            filename=file_path.name,
            content_type="audio/wav",
            language=expected_lang if audio_id != "AUDIO_MIXED" else None,
        )
        t_el = (time.perf_counter() - t0) * 1000.0

        item = {
            "id": audio_id,
            "filename": file_path.name,
            "duration_s": round(stt_result.duration_seconds, 2),
            "detected_lang": stt_result.detected_language,
            "lang_prob": round(stt_result.language_probability, 3),
            "is_silent": stt_result.is_silent,
            "transcript": stt_result.text,
            "stt_ms": round(t_el, 1),
            "service_reported_latency_ms": stt_result.latency_ms,
        }
        results["audio_queries"].append(item)
        print(f"[{audio_id}] Dur: {item['duration_s']}s | Lang: {item['detected_lang']} ({item['lang_prob']}) | Silent: {item['is_silent']} | Time: {item['stt_ms']}ms")
        print(f"  Transcript: '{item['transcript']}'\n")

    # 2. Benchmark Text Query Lifecycle
    print("\n--- STAGE 2: QUERY LIFECYCLE (LANG DETECT -> NORM -> RETRIEVAL -> LLM SSE -> TTS) ---")
    detector = LanguageDetector()
    normalizer = QueryNormalizer()

    for q in TEST_QUERIES:
        async with session_factory() as db_session:
            retriever = HybridRAGRetriever(session=db_session)
            manager = ConversationManager(session=db_session)
            # Stage A: Language Detection
            t_det = time.perf_counter()
            det_res = detector.detect(q["text"])
            det_ms = (time.perf_counter() - t_det) * 1000.0

            # Stage B: Cross-lingual Query Normalization
            t_norm = time.perf_counter()
            norm_res = normalizer.normalize_for_retrieval(q["text"], source_lang=det_res.language)
            norm_ms = (time.perf_counter() - t_norm) * 1000.0

            # Stage C: Hybrid RAG Retrieval
            t_ret = time.perf_counter()
            candidates = await retriever.retrieve(
                query=norm_res.retrieval_query,
                top_final=4,
                threshold=0.35,
            )
            ret_ms = (time.perf_counter() - t_ret) * 1000.0

            # Stage D: LLM Stream Generation via ConversationManager SSE
            t_stream = time.perf_counter()
            send_req = SendMessageRequest(
                content=q["text"],
                preferred_language=q["lang"],
                input_mode="voice",
            )
            stream_tokens = []
            ttft_ms = None
            citations = []
            is_grounded = False
            done_payload = None

            try:
                async for chunk in manager.process_message_stream(send_req):
                    for line in chunk.strip().split("\n"):
                        if line.startswith("event: token") and ttft_ms is None:
                            ttft_ms = (time.perf_counter() - t_stream) * 1000.0
                        elif line.startswith("data: "):
                            try:
                                payload = json.loads(line[6:])
                                if "token" in payload:
                                    stream_tokens.append(payload["token"])
                                elif "citations" in payload:
                                    citations = payload["citations"]
                                elif "is_grounded" in payload:
                                    done_payload = payload
                                    is_grounded = payload.get("is_grounded")
                            except Exception:
                                pass
                stream_total_ms = (time.perf_counter() - t_stream) * 1000.0
                stream_err = None
            except Exception as e:
                stream_total_ms = (time.perf_counter() - t_stream) * 1000.0
                stream_err = f"{type(e).__name__}: {str(e)}"

            full_answer = "".join(stream_tokens).strip()

            # Stage E: TTS Generation
            t_tts = time.perf_counter()
            tts_metadata = None
            tts_err = None
            if full_answer:
                try:
                    synth_req = SynthesisRequest(text=full_answer[:200], language=q["lang"])
                    wav_bytes, tts_metadata = await tts.synthesize(synth_req)
                    tts_ms = (time.perf_counter() - t_tts) * 1000.0
                except Exception as e:
                    tts_ms = (time.perf_counter() - t_tts) * 1000.0
                    tts_err = f"{type(e).__name__}: {str(e)}"
            else:
                tts_ms = 0.0

            total_e2e_ms = det_ms + norm_ms + ret_ms + stream_total_ms + tts_ms

            q_report = {
                "id": q["id"],
                "query": q["text"],
                "category": q["category"],
                "target_lang": q["lang"],
                "detected_lang": det_res.language,
                "normalized_query": norm_res.retrieval_query,
                "retrieved_chunks": len(candidates),
                "top_score": round(candidates[0].rerank_score, 3) if candidates else 0.0,
                "is_grounded": is_grounded,
                "ttft_ms": round(ttft_ms, 1) if ttft_ms else None,
                "llm_stream_ms": round(stream_total_ms, 1),
                "tts_ms": round(tts_ms, 1),
                "total_e2e_ms": round(total_e2e_ms, 1),
                "stream_error": stream_err,
                "tts_error": tts_err,
                "answer": full_answer,
            }
            results["text_queries"].append(q_report)

            print(f"[{q['id']}] Q: '{q['text']}'")
            print(f"  DetLang: {det_res.language} ({det_ms:.1f}ms) | Norm: '{norm_res.retrieval_query}' ({norm_ms:.1f}ms)")
            print(f"  Retrieval: {len(candidates)} chunks, top_score={q_report['top_score']} ({ret_ms:.1f}ms)")
            if stream_err:
                print(f"  LLM Stream Error: {stream_err} ({stream_total_ms:.1f}ms)")
            else:
                print(f"  LLM: TTFT={q_report['ttft_ms']}ms, Total={stream_total_ms:.1f}ms, Grounded={is_grounded}")
                print(f"  Answer: {full_answer[:120]}...")
            if tts_err:
                print(f"  TTS Error: {tts_err}")
            elif tts_metadata:
                print(f"  TTS: Latency={tts_ms:.1f}ms, AudioDur={tts_metadata.duration_seconds}s, Voice={tts_metadata.voice}")
            print(f"  TOTAL E2E: {total_e2e_ms:.1f}ms\n")

    # Output post-repair json artifact
    out_path = Path("C:/Users/user/.gemini/antigravity-ide/brain/69d499b4-44fb-4d0e-bb62-12bad5ec2694/scratch/post_repair_measurements.json")
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nPost-repair measurements saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
