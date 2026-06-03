"""
Полный пайплайн вопрос-ответ: Retriever + Reader
"""


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.retriever.search import SimpleRetriever
from src.reader.model import BERTSquadReader
from config.settings import settings
from src.storage.database import Database
import time

class DocQAPipeline:
    """
    Полный пайплайн: поиск чанков + извлечение ответа
    """

    def __init__(self):
        print("\n" + "=" * 60)
        print("🚀 ЗАПУСК DocQAnswer PIPELINE")
        print("=" * 60)

        print("\n📡 Инициализация Retriever...")
        self.retriever = SimpleRetriever()

        print("\n🤖 Инициализация Reader...")
        self.reader = BERTSquadReader()

        self.db = Database()
        print("📊 История запросов будет сохраняться в SQLite")

        print("\n✅ Пайплайн готов к работе!")
        print("=" * 60)

    def ask(self, question: str, top_k: int = None, user_id: str = "employee_1") -> dict:
        start_time = time.time()
        """Задать вопрос системе"""
        if top_k is None:
            top_k = settings.TOP_K_CHUNKS

        print(f"\n❓ Вопрос: {question}")

        # 1. Поиск релевантных чанков
        chunks = self.retriever.retrieve(question, top_k)

        if not chunks:
            return {
                "question": question,
                "answer": "Извините, не удалось найти релевантные документы.",
                "confidence": 0.0,
                "source": None,
                "chunks": [],
                "success": False,
                "query_id": None
            }

        # 2. Извлечение ответа из чанков
        best_answer = self.reader.best_answer_from_chunks(question, chunks)

        # 3. Формируем результат
        if best_answer.get('answer') and best_answer.get('source'):
            # ВОЗВРАЩАЕМ ИЗВЛЕЧЁННЫЙ ОТВЕТ (а не весь чанк)
            result = {
                "question": question,
                "answer": best_answer['answer'],  # ← ИЗВЛЕЧЁННЫЙ ОТВЕТ
                "full_context": best_answer['chunk_text'],  # полный контекст (для отладки)
                "confidence": best_answer['confidence'],
                "source": best_answer['source'],
                "source_chunk": best_answer['chunk_text'],
                "chunks": chunks,
                "success": True
            }
        else:
            best_chunk = chunks[0] if chunks else None
            result = {
                "question": question,
                "answer": f"Точный ответ не найден. Возможно, вас интересует: {best_chunk['text'][:500]}..." if best_chunk else "Ответ не найден.",
                "confidence": best_answer.get('confidence', 0.0),
                "source": best_chunk['source'] if best_chunk else None,
                "source_chunk": best_chunk['text'] if best_chunk else None,
                "chunks": chunks,
                "success": False
            }

        response_time = time.time() - start_time
        # 4. Сохраняем в историю и получаем ID
        query_id = None
        try:
            query_id = self.db.save_query(
                user_id=user_id,
                question=question,
                answer=result.get('answer', ''),
                source=result.get('source', ''),
                confidence=result.get('confidence', 0.0),
                success=result.get('success', False),
                response_time = response_time
            )
            print(f"📝 Запрос сохранён в историю (ID: {query_id})")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить историю: {e}")

        # Добавляем query_id в результат
        result['query_id'] = query_id
        result['response_time'] = response_time

        return result


# Интерактивный режим для тестирования
def interactive_mode():
    """Запуск интерактивного режима вопросов-ответов"""
    pipeline = DocQAPipeline()

    print("\n" + "=" * 60)
    print("💬 ИНТЕРАКТИВНЫЙ РЕЖИМ")
    print("   Задайте вопрос по документации")
    print("   Команды: 'exit' - выход, 'help' - справка")
    print("=" * 60)

    while True:
        print("\n" + "─" * 50)
        question = input("❓ Ваш вопрос: ").strip()

        if question.lower() == 'exit':
            print("👋 До свидания!")
            break
        elif question.lower() == 'help':
            print("   Просто задайте вопрос на русском языке")
            print("   Например: 'Как настроить датчик?'")
            continue
        elif not question:
            continue

        # Задаём вопрос
        result = pipeline.ask(question)

        # Выводим ответ
        print("\n" + "─" * 50)
        print(f"📝 ОТВЕТ: {result['answer']}")

        if result['source']:
            print(f"📄 ИСТОЧНИК: {result['source']}")

        print(f"📊 УВЕРЕННОСТЬ: {result['confidence']:.3f}")

        if not result['success']:
            print("\n💡 Совет: попробуйте переформулировать вопрос точнее.")


if __name__ == "__main__":
    # Простой тест
    if len(sys.argv) > 1:
        # Режим одного вопроса
        pipeline = DocQAPipeline()
        question = " ".join(sys.argv[1:])
        result = pipeline.ask(question)
        print(f"\n📝 Ответ: {result['answer']}")
        if result['source']:
            print(f"📄 Источник: {result['source']}")
    else:
        # Интерактивный режим
        interactive_mode()