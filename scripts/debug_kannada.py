import asyncio
import sys
import time

sys.path.insert(0, ".")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.application.chat.prompt_builder import PromptBuilder
from backend.src.application.chat.grounding_guard import GroundingGuard
from backend.src.domain.rag import RetrievalCandidate
from backend.src.infrastructure.llm.ollama_client import get_ollama_client

async def test():
    pb = PromptBuilder()
    chunk = RetrievalCandidate(
        chunk_id="chunk1",
        document_id="doc1",
        chunk_index=0,
        page_number=1,
        section_heading="Section 1: Historical Patronage and Inception",
        content="The Chennakeshava Temple, originally known as the Vijayanarayana Temple, was commissioned by the Hoysala ruler King Vishnuvardhana in 1117 CE. Located on the banks of the Yagachi River in Belur, the historic capital of the Hoysala Empire in Hassan district, Karnataka, the monument commemorates the military victory of King Vishnuvardhana over the Cholas in the Battle of Talakad.",
        dense_score=0.9,
        sparse_score=0.9,
        fused_score=0.9,
        rerank_score=0.99
    )
    query = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?"
    sys_p, user_p = pb.build_prompt(
        query=query,
        evidence_chunks=[chunk],
        language="kn"
    )
    print("SYSTEM PROMPT:\n", sys_p)
    print("="*60)
    print("USER PROMPT:\n", user_p)
    print("="*60)
    
    ollama = get_ollama_client()
    print("GENERATING WITH OLLAMA...")
    t0 = time.perf_counter()
    tokens = []
    async for t in ollama.stream_generate(prompt=user_p, system_prompt=sys_p):
        tokens.append(t)
    t1 = time.perf_counter()
    raw_gen = "".join(tokens)
    print(f"RAW GENERATION ({t1-t0:.2f}s):\n{raw_gen}")
    print("="*60)

    guard = GroundingGuard()
    is_grounded, verified = guard.verify_response(
        response_text=raw_gen,
        query=query,
        evidence_chunks=[chunk],
        language="kn"
    )
    print("GROUNDING VERIFICATION:")
    print("  is_grounded:", is_grounded)
    print("  verified:", verified)
    await ollama.close()

if __name__ == "__main__":
    asyncio.run(test())
