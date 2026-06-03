"""
Модуль для индексации чанков с использованием FAISS (вместо ChromaDB)
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
import pickle
from sentence_transformers import SentenceTransformer
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import settings


class FAISSIndexer:
    """
    Простой и надёжный индекс на FAISS + sentence-transformers
    """

    def __init__(self, model_name: str = None):
        print("🔧 Инициализация FAISS индекса...")

        if model_name is None:
            model_name = settings.RETRIEVER_MODEL

        print(f"   Загрузка модели: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"   ✅ Модель загружена, размер эмбеддинга: {self.model.get_sentence_embedding_dimension()}")

        self.index = None
        self.chunks = []

    def build_index(self, chunks: List[Dict[str, Any]]):
        """
        Строит индекс из списка чанков
        """
        print(f"\n📝 Построение FAISS индекса для {len(chunks)} чанков...")

        self.chunks = chunks

        # Создаём эмбеддинги для всех чанков
        print("   Создание эмбеддингов...")
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True)

        # Нормализуем для косинусного расстояния
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Создаём FAISS индекс
        import faiss
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product (косинус после нормализации)
        self.index.add(embeddings.astype('float32'))

        print(f"   ✅ Индекс создан, размерность: {dimension}, количество: {self.index.ntotal}")

        return self.index

    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Поиск top_k наиболее релевантных чанков
        """
        if top_k is None:
            top_k = settings.TOP_K_CHUNKS

        if self.index is None:
            raise RuntimeError("Индекс не построен. Сначала вызовите build_index()")

        # Создаём эмбеддинг запроса
        query_embedding = self.model.encode([query])
        query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)

        # Ищем в FAISS
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)

        # Формируем результат
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # -1 означает "не найдено"
                chunk = self.chunks[idx].copy()
                chunk["similarity"] = float(scores[0][i])  # cos similarity после нормализации
                results.append(chunk)

        return results

    def save(self, path: Path):
        """
        Сохраняет индекс и чанки на диск
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        import faiss
        faiss.write_index(self.index, str(path.with_suffix('.faiss')))

        # Сохраняем чанки и метаданные
        metadata = {
            "chunks": self.chunks,
            "model_name": self.model._modules['0'].auto_model.config.name_or_path
        }
        with open(path.with_suffix('.pkl'), 'wb') as f:
            pickle.dump(metadata, f)

        print(f"💾 Индекс сохранён в {path}")

    def load(self, path: Path):
        """
        Загружает индекс и чанки с диска
        """
        import faiss

        self.index = faiss.read_index(str(path.with_suffix('.faiss')))

        with open(path.with_suffix('.pkl'), 'rb') as f:
            metadata = pickle.load(f)

        self.chunks = metadata["chunks"]
        print(f"📂 Индекс загружен из {path}, {self.index.ntotal} чанков")


def build_faiss_index_from_chunks(
        chunks_file: Path = Path("data/chunks/all_chunks.json"),
        index_path: Path = Path("models/faiss_index")
):
    """
    Основная функция: загружает чанки и строит FAISS индекс
    """
    print("\n" + "=" * 60)
    print("🔨 ПОСТРОЕНИЕ FAISS ИНДЕКСА")
    print("=" * 60)

    # 1. Загружаем чанки
    print(f"\n📂 Загрузка чанков из {chunks_file}")
    if not chunks_file.exists():
        print(f"❌ Файл с чанками не найден: {chunks_file}")
        print("   Сначала запустите: python src/data/loader.py")
        return None

    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"✅ Загружено чанков: {len(chunks)}")

    if len(chunks) == 0:
        print("❌ Нет чанков для индексации")
        return None

    # 2. Строим индекс
    print("\n" + "-" * 40)
    indexer = FAISSIndexer()
    indexer.build_index(chunks)

    # 3. Сохраняем индекс
    indexer.save(index_path)

    # 4. Тестовый поиск
    print("\n🔍 Тестовый поиск по запросу 'калибровка':")
    results = indexer.search("калибровка", top_k=2)

    if results:
        for i, r in enumerate(results):
            print(f"   {i + 1}. [{r['source']}] {r['text'][:100]}...")
            print(f"      Сходство: {r['similarity']:.4f}")
    else:
        print("   Ничего не найдено")

    print("\n✅ FAISS ИНДЕКС УСПЕШНО ПОСТРОЕН")
    print("=" * 60)

    return indexer


if __name__ == "__main__":
    build_faiss_index_from_chunks()