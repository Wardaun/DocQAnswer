"""
Экспорт запросов с дизлайками для ручной разметки
"""

import sqlite3
import json
import csv
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/docqanswer.db")


def export_to_json():
    """Экспорт в JSON для дальнейшей обработки"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Запросы с дизлайками
    cursor.execute("""
        SELECT 
            q.id,
            q.question,
            q.answer,
            q.source_doc,
            q.confidence,
            q.timestamp,
            f.is_positive,
            f.timestamp as feedback_time
        FROM query_history q
        JOIN feedback f ON q.id = f.query_id
        WHERE f.is_positive = 0
        ORDER BY q.timestamp DESC
    """)

    rows = cursor.fetchall()

    # Преобразуем в список словарей
    failed_queries = []
    for row in rows:
        failed_queries.append({
            "query_id": row["id"],
            "question": row["question"],
            "system_answer": row["answer"],
            "source": row["source_doc"],
            "confidence": row["confidence"],
            "timestamp": row["timestamp"],
            "feedback_time": row["feedback_time"]
        })

    # Сохраняем в JSON
    output_file = Path("data/finetuning/failed_queries.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(failed_queries, f, ensure_ascii=False, indent=2)

    print(f"✅ Экспортировано {len(failed_queries)} запросов с дизлайками в {output_file}")

    conn.close()
    return failed_queries


def export_to_csv():
    """Экспорт в CSV для ручной разметки в Excel"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            q.id,
            q.question,
            q.answer,
            q.source_doc,
            q.confidence,
            q.timestamp,
            f.timestamp as feedback_time
        FROM query_history q
        JOIN feedback f ON q.id = f.query_id
        WHERE f.is_positive = 0
        ORDER BY q.timestamp DESC
    """)

    rows = cursor.fetchall()

    # Сохраняем в CSV
    output_file = Path("data/finetuning/failed_queries.csv")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Вопрос', 'Ответ системы', 'Источник', 'Уверенность', 'Время запроса', 'Время оценки'])
        writer.writerows(rows)

    print(f"✅ Экспортировано {len(rows)} запросов в {output_file}")

    conn.close()


def show_statistics():
    """Показывает статистику по оценкам"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Общая статистика
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT q.id) as total_queries,
            SUM(CASE WHEN f.is_positive = 1 THEN 1 ELSE 0 END) as likes,
            SUM(CASE WHEN f.is_positive = 0 THEN 1 ELSE 0 END) as dislikes,
            COUNT(f.id) as total_feedback
        FROM query_history q
        LEFT JOIN feedback f ON q.id = f.query_id
    """)

    stats = cursor.fetchone()
    total_queries, likes, dislikes, total_feedback = stats

    print("\n" + "=" * 60)
    print("📊 СТАТИСТИКА ОБРАТНОЙ СВЯЗИ")
    print("=" * 60)
    print(f"📝 Всего запросов: {total_queries}")
    print(f"👍 Лайков: {likes or 0}")
    print(f"👎 Дизлайков: {dislikes or 0}")

    if total_feedback and total_feedback > 0:
        positive_rate = (likes or 0) / total_feedback * 100
        print(f"📈 Положительных оценок: {positive_rate:.1f}%")

    print("=" * 60)

    conn.close()


def create_template_for_labeling():
    """
    Создаёт шаблон для ручной разметки правильных ответов
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            q.id,
            q.question,
            q.source_doc
        FROM query_history q
        JOIN feedback f ON q.id = f.query_id
        WHERE f.is_positive = 0
        ORDER BY q.timestamp DESC
    """)

    rows = cursor.fetchall()

    # Создаём шаблон для разметки
    labeling_data = []
    for row in rows:
        # Получаем оригинальный чанк из базы (нужно достать из source_chunk)
        labeling_data.append({
            "query_id": row[0],
            "question": row[1],
            "source_doc": row[2],
            "correct_answer": "",  # ← Заполнить вручную
            "context": ""  # ← Будет заполнено из all_chunks.json
        })

    output_file = Path("data/finetuning/labeling_template.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(labeling_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Шаблон для разметки создан: {output_file}")
    print(f"   Откройте файл и заполните поле 'correct_answer' для каждого вопроса")

    conn.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("📤 ЭКСПОРТ НЕУДАЧНЫХ ЗАПРОСОВ")
    print("=" * 60)

    # Показываем статистику
    show_statistics()

    # Экспортируем
    export_to_json()
    export_to_csv()
    create_template_for_labeling()

    print("\n✅ Готово!")
    print("\n📁 Файлы сохранены в папке: data/finetuning/")
    print("   1. failed_queries.json - полные данные")
    print("   2. failed_queries.csv - можно открыть в Excel")
    print("   3. labeling_template.json - шаблон для разметки правильных ответов")