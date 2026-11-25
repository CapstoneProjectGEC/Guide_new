import httpx
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

QUESTIONS = [
    {
        "id": 1,
        "category": "Material & Stone",
        "question": "ಬೇಲೂರು ದೇವಾಲಯವನ್ನು ಯಾವ ಕಲ್ಲಿನಿಂದ ನಿರ್ಮಿಸಲಾಗಿದೆ?",
        "expected_facts": ["ಬಳಪದ ಕಲ್ಲು", "soapstone", "chloritic schist", "ಕ್ಲೋರಿಟಿಕ್"],
        "is_grounded_expected": True
    },
    {
        "id": 2,
        "category": "Madanika Counts",
        "question": "ಬೇಲೂರಿನಲ್ಲಿ ಒಟ್ಟು ಎಷ್ಟು ಮದನಿಕಾ ಶಿಲ್ಪಗಳಿವೆ?",
        "expected_facts": ["42", "೩೮", "38", "೪"],
        "is_grounded_expected": True
    },
    {
        "id": 3,
        "category": "Darpana Sundari",
        "question": "ದರ್ಪಣ ಸುಂದರಿ ಶಿಲ್ಪದ ವಿಶೇಷತೆ ಏನು?",
        "expected_facts": ["ದರ್ಪಣ", "mirror", "ಕನ್ನಡಿ", "ಸುಂದರಿ"],
        "is_grounded_expected": True
    },
    {
        "id": 4,
        "category": "Wall Friezes",
        "question": "ದೇವಾಲಯದ ತಳಭಾಗದಲ್ಲಿರುವ ಆನೆಗಳ ಕೆತ್ತನೆಗಳ ಸಂಖ್ಯೆ ಎಷ್ಟು?",
        "expected_facts": ["650", "೬೫೦", "ಆನೆ"],
        "is_grounded_expected": True
    },
    {
        "id": 5,
        "category": "Garbhagriha Idol",
        "question": "ಗರ್ಭಗುಡಿಯಲ್ಲಿರುವ ಚೆನ್ನಕೇಶವ ವಿಗ್ರಹದ ಎತ್ತರ ಎಷ್ಟು?",
        "expected_facts": ["6", "೬", "ಅಡಿ", "foot"],
        "is_grounded_expected": True
    },
    {
        "id": 6,
        "category": "Historical Victory",
        "question": "ವಿಷ್ಣುವರ್ಧನ ರಾಜನು ಯಾವ ವಿಜಯದ ನೆನಪಿಗಾಗಿ ದೇವಾಲಯವನ್ನು ಕಟ್ಟಿಸಿದನು?",
        "expected_facts": ["ತಲಕಾಡು", "ಚೋಳ", "Talakad", "Chola"],
        "is_grounded_expected": True
    },
    {
        "id": 7,
        "category": "UNESCO Recognition",
        "question": "ಬೇಲೂರು ದೇವಾಲಯಕ್ಕೆ ಯುನೆಸ್ಕೋ ವಿಶ್ವ ಪರಂಪರೆ ತಾಣದ ಮಾನ್ಯತೆ ಯಾವಾಗ ದೊರೆಯಿತು?",
        "expected_facts": ["2023", "೨೦೨೩", "ಯುನೆಸ್ಕೋ"],
        "is_grounded_expected": True
    },
    {
        "id": 8,
        "category": "Platform Architecture",
        "question": "ದೇವಾಲಯವು ಯಾವ ಆಕಾರದ ಜಗತಿ ವೇದಿಕೆಯ ಮೇಲೆ ನಿಂತಿದೆ?",
        "expected_facts": ["ಜಗತಿ", "ನಕ್ಷತ್ರ", "star", "stellate"],
        "is_grounded_expected": True
    },
    {
        "id": 9,
        "category": "Master Sculptors",
        "question": "ಬೇಲೂರು ದೇವಾಲಯದ ಶಿಲ್ಪಿಗಳು ಯಾರು?",
        "expected_facts": ["ದಾಸೋಜ", "ಮಲ್ಲಿತಮ್ಮ", "Dasoja", "Mallitamma"],
        "is_grounded_expected": True
    },
    {
        "id": 10,
        "category": "Main Sanctum Deities",
        "question": "ಗರ್ಭಗುಡಿಯ ಮುಖ್ಯ ದೇವರು ಯಾರು?",
        "expected_facts": ["ಚೆನ್ನಕೇಶವ", "ವಿಷ್ಣು", "Chennakeshava", "Vishnu"],
        "is_grounded_expected": True
    },
    {
        "id": 11,
        "category": "Out-of-Scope Fallback",
        "question": "ಬೆಂಗಳೂರಿನ ಇಂದಿನ ಹವಾಮಾನ ಹೇಗಿದೆ?",
        "expected_facts": ["ಲಭ್ಯವಿಲ್ಲ"],
        "is_grounded_expected": False
    }
]

def test_unseen():
    results = []
    print("=== Testing 10 Unseen Kannada Questions + 1 Out-of-Scope Fallback ===\n")

    with httpx.Client(timeout=30.0) as client:
        for q in QUESTIONS:
            payload = {
                "content": q["question"],
                "preferred_language": "kn",
                "input_mode": "text"
            }
            t0 = time.perf_counter()
            tokens = []
            citations = []
            done_payload = {}

            with client.stream("POST", "http://127.0.0.1:8000/api/v1/chat/stream", json=payload) as resp:
                for line in resp.iter_lines():
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:].strip())
                            if "token" in data:
                                tokens.append(data["token"])
                            if "citations" in data:
                                citations = data["citations"]
                            if "is_grounded" in data:
                                done_payload = data
                        except Exception:
                            pass
            t1 = time.perf_counter()
            tot_ms = int((t1 - t0) * 1000)
            ans = "".join(tokens).strip()
            grounded = done_payload.get("is_grounded", False)
            rep_ms = done_payload.get("latency_ms", tot_ms)

            # Check expected facts
            facts_found = any(f.lower() in ans.lower() for f in q["expected_facts"])
            status_ok = (grounded == q["is_grounded_expected"]) and (facts_found or not q["is_grounded_expected"])

            res_entry = {
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "latency_ms": tot_ms,
                "reported_ms": rep_ms,
                "is_grounded": grounded,
                "expected_grounded": q["is_grounded_expected"],
                "citations_count": len(citations),
                "citations": [f"p.{c.get('page_number')}: {c.get('section_heading')}" for c in citations],
                "answer": ans,
                "passed": status_ok
            }
            results.append(res_entry)

            print(f"[{q['id']}/11] {q['category']}: {q['question']}")
            print(f"  Latency: {tot_ms} ms (Reported: {rep_ms} ms) | Grounded: {grounded} (Expected: {q['is_grounded_expected']})")
            print(f"  Citations ({len(citations)}): {[c.get('section_heading') for c in citations]}")
            print(f"  Answer: {ans}")
            print(f"  Result: {'PASS' if status_ok else 'CHECK'}\n")

    with open("logs/unseen_questions_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("All results saved to logs/unseen_questions_benchmark.json")

if __name__ == "__main__":
    test_unseen()

