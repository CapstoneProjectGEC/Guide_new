import pymysql
import sys

sys.stdout.reconfigure(encoding="utf-8")
conn = pymysql.connect(host="localhost", user="root", password="root", port=3306, database="karnataka_tourism", charset="utf8mb4")
cur = conn.cursor()
cur.execute("SELECT id, session_id, role, content, detected_language, latency_ms, is_grounded, created_at FROM chat_messages WHERE session_id = 'a7579481-9567-4f34-8ef9-8a1996b460d7' ORDER BY created_at ASC")
for r in cur.fetchall():
    print("ID:", r[0])
    print("Role:", r[2])
    print("Language:", r[4])
    print("Latency:", r[5])
    print("Grounded:", r[6])
    print("Content:\n", r[3])
    print("-" * 50)

