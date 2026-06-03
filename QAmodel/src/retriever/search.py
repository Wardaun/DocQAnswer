"""
Простой поиск с использованием FAISS индекса
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.retriever.faiss_indexer import FAISSIndexer

from config.settings import settings


class SimpleRetriever:
    def __init__(self):
        index_path = Path("models/faiss_index")

        if not index_path.with_suffix('.faiss').exists():
            raise RuntimeError(f"Индекс не найден: {index_path}. Сначала запустите faiss_indexer.py")

        self.indexer = FAISSIndexer()
        self.indexer.load(index_path)

    def retrieve(self, query: str, top_k: int = None) -> list:
        return self.indexer.search(query, top_k)


if __name__ == "__main__":
    retriever = SimpleRetriever()

    print("\n🔍 ТЕСТ ПОИСКА")
    print("-" * 40)

    queries = [
        "Как настроить датчик?",
        "калибровка весов",
        "батарейки"
    ]

    for q in queries:
        print(f"\n📝 Вопрос: {q}")
        results = retriever.retrieve(q)

        if results:
            for i, r in enumerate(results):
                print(f"   {i + 1}. [{r['source']}] {r['text'][:80]}...")
                print(f"      (сходство: {r['similarity']:.3f})")
        else:
            print("   ❌ Ничего не найдено")