import asyncio
import sys
import time

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.application.chat.prompt_builder import PromptBuilder
from backend.src.application.chat.grounding_guard import GroundingGuard
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.llm.ollama_client import get_ollama_client

async def profile_query(query: str, lang: str):
    print(f"\n=======================================================")
    print(f"PROFILING QUERY ({lang}): {query}")
    print(f"=======================================================")
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        t0 = time.perf_counter()
        
        # 1. Detection
        detector = LanguageDetector()
        det = detector.detect(query)
        t_det = time.perf_counter()
        print(f"1. Language Detection: {det.language} (took {(t_det - t0)*1000:.1f}ms)")
        
        # 2. Normalization
        normalizer = QueryNormalizer()
        norm = normalizer.normalize_for_retrieval(query, source_lang=lang)
        t_norm = time.perf_counter()
        print(f"2. Query Normalization: '{norm.retrieval_query}' (strategy: {norm.strategy_used}, took {(t_norm - t_det)*1000:.1f}ms)")
        
        # 3. Retrieval
        retriever = HybridRAGRetriever(session=session)
        candidates = await retriever.retrieve(norm.retrieval_query, top_final=4, threshold=0.35)
        t_ret = time.perf_counter()
        print(f"3. Retrieval: {len(candidates)} candidates (took {(t_ret - t_norm)*1000:.1f}ms)")
        
        # 4. Prompt construction
        pb = PromptBuilder()
        sys_p, user_p = pb.build_prompt(query, candidates, language=lang)
        t_pb = time.perf_counter()
        print(f"4. Prompt Builder: sys {len(sys_p)} chars, user {len(user_p)} chars (took {(t_pb - t_ret)*1000:.1f}ms)")
        
        # 5. LLM Generation
        ollama = get_ollama_client()
        tokens = []
        async for token in ollama.stream_generate(prompt=user_p, system_prompt=sys_p):
            tokens.append(token)
        t_llm = time.perf_counter()
        raw_res = "".join(tokens).strip()
        print(f"5. LLM Generation: {len(tokens)} tokens, length {len(raw_res)} chars (took {(t_llm - t_pb)*1000:.1f}ms)")
        print(f"   Raw Output:\n   '{raw_res}'")
        
        # 6. Verification
        guard = GroundingGuard()
        is_grounded, verified = guard.verify_response(raw_res, query, candidates, language=lang)
        t_guard = time.perf_counter()
        print(f"6. Grounding Guard: is_grounded={is_grounded} (took {(t_guard - t_llm)*1000:.1f}ms)")
        print(f"   Verified Output:\n   '{verified}'")
        
        print(f"\nTOTAL PIPELINE TIME: {(t_guard - t0)*1000:.1f}ms")
        await ollama.close()

async def main():
    await profile_query("Who built the Chennakeshava Temple at Belur and when?", "en")
    await profile_query("ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?", "kn")

if __name__ == "__main__":
    asyncio.run(main())

