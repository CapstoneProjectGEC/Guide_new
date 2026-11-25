"""Controlled benchmark script to measure voice & chat stages and record baseline metrics."""

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
    print("PHASE B: REPRODUCIBLE BASELINE BENCHMARK")
    print("=" * 80)

    # 1. Audio STT Benchmarks
    print("\n--- 1. SPEECH RECOGNITION (STT) STAGE ---")
    for tag, audio_path, lang in AUDIO_FIXTURES:
        if not audio_path.exists():
            print(f"Skipping {tag}: file not found {audio_path}")
            continue
        audio_bytes = audio_path.read_bytes()
        t0 = time.perf_counter()
        res = await stt.transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            filename=audio_path.name,
            content_type="audio/wav",
            language=lang,
        )
        stt_elapsed = (time.perf_counter() - t0) * 1000.0
        audio_res = {
            "id": tag,
            "filename": audio_path.name,
            "duration_s": res.duration_seconds,
            "stt_latency_ms": round(res.latency_ms or stt_elapsed, 1),
            "detected_lang": res.detected_language,
            "is_silent": res.is_silent,
            "transcript": res.text,
        }
        results["audio_queries"].append(audio_res)
        print(f"[{tag}] Dur: {res.duration_seconds}s | Latency: {audio_res['stt_latency_ms']}ms | Lang: {res.detected_language} | Silent: {res.is_silent}")
        print(f"  Transcript: '{res.text}'")

    # 2. Text Query Benchmarks (Detailed Pipeline Stage Timing)
    print("\n--- 2. CONVERSATIONAL RAG & GENERATION STAGES ---")
    for q in TEST_QUERIES:
        async with session_factory() as s:
            mgr = ConversationManager(session=s)
            detector = LanguageDetector()
            normalizer = QueryNormalizer()
            retriever = HybridRAGRetriever(session=s)

            # Stage A: Language Detection
            t_det = time.perf_counter()
            det_res = detector.detect(q["text"], fallback_language=q["lang"])
            det_ms = (time.perf_counter() - t_det) * 1000.0

            # Stage B: Normalization
            t_norm = time.perf_counter()
            norm_res = normalizer.normalize_for_retrieval(q["text"], source_lang=det_res.language)
            norm_ms = (time.perf_counter() - t_norm) * 1000.0

            # Stage C: Retrieval & Re-ranking
            t_ret = time.perf_counter()
            candidates = await retriever.retrieve(norm_res.retrieval_query, top_final=4, threshold=0.35)
            ret_ms = (time.perf_counter() - t_ret) * 1000.0

            # Stage D: Stream Generation (SSE)
            req = SendMessageRequest(content=q["text"], preferred_language=q["lang"])
            t_stream = time.perf_counter()
            stream_tokens = []
            citations = []
            ttft_ms = None
            is_grounded = None
            done_payload = None

            try:
                async for event_str in mgr.process_message_stream(req):
                    for line in event_str.splitlines():
                        if line.startswith("event: citations"):
                            pass
                        elif line.startswith("event: token"):
                            if ttft_ms is None:
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

    # Output baseline json artifact
    out_path = Path("C:/Users/user/.gemini/antigravity-ide/brain/69d499b4-44fb-4d0e-bb62-12bad5ec2694/scratch/baseline_measurements.json")
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nBaseline measurements saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
