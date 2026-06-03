"""
Модуль для разбиения документов на чанки (фрагменты) оптимального размера
"""

import re
from pathlib import Path
from typing import List, Dict, Any
import json

# Попробуем импортировать settings (если не получится - используем значения по умолчанию)
try:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config.settings import settings

    CHUNK_SIZE = settings.CHUNK_SIZE
    CHUNK_OVERLAP = settings.CHUNK_OVERLAP
except:
    CHUNK_SIZE = 512  # примерное количество символов
    CHUNK_OVERLAP = 50


class DocumentChunker:
    """
    Разбивает документы на чанки с учётом границ предложений
    """

    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_by_sentences(self, text: str) -> List[str]:
        """
        Разбивает текст на предложения (простое правило по .!?)
        """
        # Разбиваем по .!? с последующим пробелом или концом строки
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Убираем пустые предложения
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def chunk_sentences(self, sentences: List[str]) -> List[str]:
        """
        Объединяет предложения в чанки заданного размера с перекрытием
        """
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # Если одно предложение длиннее chunk_size - разбиваем принудительно
            if sentence_len > self.chunk_size:
                # Сохраняем текущий чанк, если он не пуст
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Разбиваем длинное предложение на части
                for i in range(0, sentence_len, self.chunk_size - self.overlap):
                    part = sentence[i:i + self.chunk_size]
                    chunks.append(part)
                continue

            # Если добавление предложения превышает размер - начинаем новый чанк
            if current_length + sentence_len + 1 > self.chunk_size:
                # Сохраняем текущий чанк
                if current_chunk:
                    chunks.append(' '.join(current_chunk))

                # Перекрытие: оставляем несколько последних предложений
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) + 1 <= self.overlap:
                        overlap_sentices = [s] + overlap_sentences
                        overlap_length += len(s) + 1
                    else:
                        break

                current_chunk = overlap_sentences
                current_length = overlap_length

            current_chunk.append(sentence)
            current_length += sentence_len + 1  # +1 для пробела

        # Добавляем последний чанк
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def chunk_document(self, text: str, source: str) -> List[Dict[str, Any]]:
        """
        Принимает текст документа и возвращает список чанков с метаданными

        Args:
            text: текст документа
            source: название/путь к исходному документу

        Returns:
            Список словарей: [{"id": 0, "text": "...", "source": "...", "chunk_index": 0}, ...]
        """
        sentences = self.split_by_sentences(text)
        chunks_text = self.chunk_sentences(sentences)

        chunks = []
        for i, chunk_text in enumerate(chunks_text):
            chunks.append({
                "id": f"{source}_{i}",
                "text": chunk_text,
                "source": source,
                "chunk_index": i,
                "length": len(chunk_text)
            })

        return chunks

    def chunk_multiple_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Обрабатывает несколько документов

        Args:
            documents: список словарей [{"text": "...", "source": "doc1.txt"}, ...]

        Returns:
            Список всех чанков из всех документов
        """
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(doc["text"], doc["source"])
            all_chunks.extend(chunks)
            print(f"📄 {doc['source']}: разбит на {len(chunks)} чанков")

        return all_chunks


# Вспомогательная функция для сохранения чанков в JSON
def save_chunks(chunks: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Сохраняет чанки в JSON файл
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено {len(chunks)} чанков в {output_path}")


# Простой тест при запуске файла напрямую
if __name__ == "__main__":
    # Тестовый документ
    test_text = """
    Первый шаг: откройте крышку прибора.
    Второй шаг: вставьте батарейки CR2032, соблюдая полярность.
    Третий шаг: закройте крышку до щелчка.
    Если прибор не включается, проверьте правильность установки батареек.
    При длительном хранении батарейки необходимо извлечь.
    """

    chunker = DocumentChunker(chunk_size=200, overlap=30)
    chunks = chunker.chunk_document(test_text, "test_doc.txt")

    print(f"\n✅ Тест пройден. Создано {len(chunks)} чанков:")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Чанк {i} ---")
        print(f"Источник: {chunk['source']}")
        print(f"Длина: {chunk['length']} символов")
        print(f"Текст: {chunk['text'][:100]}...")