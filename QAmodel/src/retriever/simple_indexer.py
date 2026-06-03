"""
Простой индекс без FAISS (на случай проблем с FAISS на Windows)
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


class SimpleIndexer:
    """
    Индекс на основе косинусной близости (без FAISS)
    """

    def __init__(self, model_name: str = None):
        print("🔧 Инициализация SimpleIndexer (без FAISS)...")

        if model_name is None:
            model_name = settings.RETRIEVER_MODEL

        print(f"   Загрузка модели: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"   ✅ Модель загружена")

        self.embeddings = None
        self.chunks = []

    def build_index(self, chunks: List[Dict[str, Any]]):
        """Строит индекс из списка чанков"""
        print(f"\n📝 Построение индекса для {len(chunks)} чанков...")

        self.chunks = chunks

        # Создаём эмбеддинги для всех чанков
        print("   Создание эмбеддингов...")
        texts = [chunk["text"] for chunk in chunks]
        self.embeddings = self.model.encode(texts, show_progress_bar=True)

        # Нормализуем для косинусного расстояния
        self.embeddings = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)

        print(f"   ✅ Индекс создан, размерность: {self.embeddings.shape}")

    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Поиск top_k наиболее релевантных чанков"""
        if top_k is None:
            top_k = settings.TOP_K_CHUNKS

        if self.embeddings is None:
            raise RuntimeError("Индекс не построен. Сначала вызовите build_index()")

        # Создаём эмбеддинг запроса
        query_embedding = self.model.encode([query])
        query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)

        # Вычисляем косинусную близость
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()

        # Получаем top_k индексов
        if len(similarities) > top_k:
            top_indices = np.argsort(similarities)[-top_k:][::-1]
        else:
            top_indices = np.argsort(similarities)[::-1]

        # Формируем результат
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx].copy()
            chunk["similarity"] = float(similarities[idx])
            results.append(chunk)

        return results

    def save(self, path: Path):
        """Сохраняет индекс и чанки на диск"""
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "embeddings": self.embeddings,
            "chunks": self.chunks,
            "model_name": self.model._modules['0'].auto_model.config.name_or_path
        }
        with open(path.with_suffix('.pkl'), 'wb') as f:
            pickle.dump(data, f)

        print(f"💾 Индекс сохранён в {path}")

    def load(self, path: Path):
        """Загружает индекс и чанки с диска"""
        with open(path.with_suffix('.pkl'), 'rb') as f:
            data = pickle.load(f)

        self.embeddings = data["embeddings"]
        self.chunks = data["chunks"]
        print(f"📂 Индекс загружен из {path}, {len(self.chunks)} чанков")


def build_simple_index_from_chunks(
        chunks_file: Path = Path("data/chunks/all_chunks.json"),
        index_path: Path = Path("models/simple_index")
):
    """Основная функция: загружает чанки и строит индекс"""
    print("\n" + "=" * 60)
    print("🔨 ПОСТРОЕНИЕ ПРОСТОГО ИНДЕКСА")
    print("=" * 60)

    # 1. Загружаем чанки
    print(f"\n📂 Загрузка чанков из {chunks_file}")
    if not chunks_file.exists():
        print(f"❌ Файл с чанками не найден: {chunks_file}")
        return None

    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"✅ Загружено чанков: {len(chunks)}")

    # 2. Строим индекс
    indexer = SimpleIndexer()
    indexer.build_index(chunks)

    # 3. Сохраняем индекс
    indexer.save(index_path)

    # 4. Тестовый поиск
    print("\n🔍 Тестовый поиск по запросу 'настройка':")
    results = indexer.search("настройка", top_k=2)

    if results:
        for i, r in enumerate(results):
            print(f"   {i + 1}. [{r['source']}] {r['text'][:100]}...")
            print(f"      Сходство: {r['similarity']:.4f}")

    print("\n✅ ПРОСТОЙ ИНДЕКС ПОСТРОЕН")
    return indexer


if __name__ == "__main__":
    build_simple_index_from_chunks()