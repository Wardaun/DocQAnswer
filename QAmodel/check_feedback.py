import sqlite3
from pathlib import Path

DB_PATH = Path("data/docqanswer.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Запрос с объединением таблиц
cursor.execute("""
    SELECT 
        q.id,
        q.question,
        q.answer,
        q.confidence,
        f.is_positive,
        f.timestamp as feedback_time
    FROM query_history q
    LEFT JOIN feedback f ON q.id = f.query_id
    ORDER BY q.timestamp DESC
    LIMIT 10
""")

rows = cursor.fetchall()

print("=" * 70)
print("📊 ЗАПРОСЫ И ОЦЕНКИ")
print("=" * 70)

for row in rows:
    print(f"\n🆔 Запрос #{row[0]}")
    print(f"   ❓ {row[1][:60]}...")
    print(f"   📝 {row[2][:80]}...")
    print(f"   🎯 Уверенность: {row[3]:.3f}")

    if row[4] is not None:
        rating = "👍 Лайк" if row[4] == 1 else "👎 Дизлайк"
        print(f"   📊 Оценка: {rating} ({row[5]})")
    else:
        print(f"   📊 Оценка: не оценено")
    print("-" * 40)

conn.close()