import sqlite3
from pathlib import Path

# Корень проекта (где лежат папки src, data, config)
ROOT_DIR = Path(__file__).parent.parent.parent
DB_PATH = ROOT_DIR / "data" / "docqanswer.db"


class Database:
    def __init__(self):
        # Убедимся, что папка data существует
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = DB_PATH
        self._init_tables()
        print(f"✅ База данных инициализирована: {DB_PATH}")

    def _init_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT,
                    source_doc TEXT,
                    confidence REAL,
                    response_time REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Для существующей базы данных добавим колонку, если её нет
            try:
                cursor.execute("ALTER TABLE query_history ADD COLUMN response_time REAL")
            except sqlite3.OperationalError:
                pass  # Колонка уже существует

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id INTEGER,
                    is_positive BOOLEAN,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (query_id) REFERENCES query_history(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failed_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    retrieved_chunks TEXT,
                    max_confidence REAL,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def save_query(self, user_id: str, question: str, answer: str, source: str, confidence: float,
                   success: bool, response_time: float = None) -> int:
        """
        Сохраняет запрос пользователя в историю

        Returns:
            id сохранённой записи
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO query_history (user_id, question, answer, source_doc, confidence, response_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, question, answer, source, confidence, response_time))
            conn.commit()
            return cursor.lastrowid

    def save_feedback(self, query_id: int, is_positive: bool) -> None:
        """
        Сохраняет оценку ответа (лайк/дизлайк)

        Args:
            query_id: ID запроса из query_history
            is_positive: True = лайк, False = дизлайк
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (query_id, is_positive)
                VALUES (?, ?)
            """, (query_id, is_positive))
            conn.commit()
            print(f"✅ Оценка {'👍' if is_positive else '👎'} сохранена для запроса {query_id}")


# Простая проверка
if __name__ == "__main__":
    db = Database()
    print(f"✅ База данных готова: {DB_PATH}")

    # Проверим, что файл создался
    if DB_PATH.exists():
        print(f"   Файл создан, размер: {DB_PATH.stat().st_size} байт")
    else:
        print("   ❌ Файл не создался")