import sqlite3
from pathlib import Path

DB_PATH = Path("data/docqanswer.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT id, user_id, question, answer, source_doc, confidence, timestamp 
    FROM query_history 
    ORDER BY timestamp DESC
    LIMIT 10
""")

rows = cursor.fetchall()

print("=" * 60)
print("📊 ПОСЛЕДНИЕ ЗАПРОСЫ")
print("=" * 60)

if rows:
    for row in rows:
        print(f"\n🆔 {row[0]} | 👤 {row[1]} | 📅 {row[6]}")
        print(f"   ❓ {row[2][:80]}...")
        print(f"   📝 {row[3][:100]}...")
        print(f"   📄 {row[4]} | 🎯 {row[5]:.3f}")
else:
    print("Нет сохранённых запросов")

conn.close()