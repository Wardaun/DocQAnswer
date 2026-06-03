"""
Модуль для загрузки документов из различных форматов
"""
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pathlib import Path
from typing import List, Dict, Any
import json
from src.data.chunker import DocumentChunker, save_chunks

# Попытка импорта для работы с разными форматами
try:
    import docx

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️  python-docx не установлен. Файлы .docx не будут поддерживаться.")

try:
    import PyPDF2

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️  PyPDF2 не установлен. Файлы .pdf не будут поддерживаться.")


class DocumentLoader:
    """
    Загружает документы из папки и преобразует в текст
    """

    @staticmethod
    def load_text_file(file_path: Path) -> str:
        """Загружает обычный текстовый файл"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def load_docx_file(file_path: Path) -> str:
        """Загружает DOCX файл (если установлен python-docx)"""
        if not DOCX_AVAILABLE:
            raise ImportError("Установите python-docx: pip install python-docx")

        import docx
        doc = docx.Document(file_path)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        return text

    @staticmethod
    def load_pdf_file(file_path: Path) -> str:
        """Загружает PDF файл (если установлен PyPDF2)"""
        if not PDF_AVAILABLE:
            raise ImportError("Установите PyPDF2: pip install PyPDF2")

        import PyPDF2
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text()
        return text

    def load_document(self, file_path: Path) -> Dict[str, str]:
        """
        Определяет формат файла и загружает его

        Returns:
            {"source": "имя_файла", "text": "содержимое"}
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        # Определяем формат по расширению
        extension = file_path.suffix.lower()

        if extension == '.txt':
            text = self.load_text_file(file_path)
        elif extension == '.docx':
            text = self.load_docx_file(file_path)
        elif extension == '.pdf':
            text = self.load_pdf_file(file_path)
        else:
            raise ValueError(f"Неподдерживаемый формат: {extension}")

        return {
            "source": file_path.name,
            "text": text
        }

    def load_all_from_directory(self, directory: Path) -> List[Dict[str, str]]:
        """
        Загружает все поддерживаемые документы из папки

        Returns:
            Список документов: [{"source": "...", "text": "..."}, ...]
        """
        documents = []
        supported_extensions = ['.txt', '.docx', '.pdf']

        # Создаём папку, если её нет
        directory.mkdir(parents=True, exist_ok=True)

        # Ищем все файлы с поддерживаемыми расширениями
        for ext in supported_extensions:
            for file_path in directory.glob(f"*{ext}"):
                try:
                    doc = self.load_document(file_path)
                    documents.append(doc)
                    print(f"📖 Загружен: {file_path.name} ({len(doc['text'])} символов)")
                except Exception as e:
                    print(f"❌ Ошибка загрузки {file_path.name}: {e}")

        return documents


def process_all_documents(
        raw_dir: Path = Path("data/raw"),
        chunks_dir: Path = Path("data/chunks"),
        chunk_size: int = 512,
        overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Основная функция: загружает все документы, разбивает на чанки, сохраняет результат
    """
    print("\n" + "=" * 60)
    print("🚀 НАЧАЛО ОБРАБОТКИ ДОКУМЕНТОВ")
    print("=" * 60)

    # 1. Загружаем документы
    loader = DocumentLoader()
    documents = loader.load_all_from_directory(raw_dir)

    if not documents:
        print(f"⚠️  Документы не найдены в {raw_dir}")
        print(f"   Поместите файлы (.txt, .docx, .pdf) в папку {raw_dir}")
        return []

    print(f"\n📚 Всего загружено документов: {len(documents)}")

    # 2. Разбиваем на чанки
    chunker = DocumentChunker(chunk_size=chunk_size, overlap=overlap)
    all_chunks = chunker.chunk_multiple_documents(documents)

    # 3. Проверяем, что чанки создались
    if not all_chunks:
        print("❌ Не удалось создать чанки!")
        return []

    print(f"\n📊 Создано чанков: {len(all_chunks)}")

    # 4. Сохраняем чанки
    output_file = chunks_dir / "all_chunks.json"
    print(f"\n💾 Сохраняем в {output_file}")

    try:
        # Создаём папку, если её нет
        chunks_dir.mkdir(parents=True, exist_ok=True)

        # Сохраняем JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)

        # Проверяем, что файл создался
        if output_file.exists():
            file_size = output_file.stat().st_size
            print(f"✅ Файл сохранён! Размер: {file_size} байт")
        else:
            print(f"❌ Ошибка: файл не создался!")

    except Exception as e:
        print(f"❌ Ошибка при сохранении: {e}")
        return []

    # 5. Выводим статистику
    print("\n" + "=" * 60)
    print("📊 СТАТИСТИКА")
    print("=" * 60)
    print(f"Всего документов: {len(documents)}")
    print(f"Всего чанков: {len(all_chunks)}")

    if all_chunks:
        avg_length = sum(c['length'] for c in all_chunks) / len(all_chunks)
        print(f"Средняя длина чанка: {avg_length:.0f} символов")
        print(f"Минимальный чанк: {min(c['length'] for c in all_chunks)} символов")
        print(f"Максимальный чанк: {max(c['length'] for c in all_chunks)} символов")

    print("\n✅ ОБРАБОТКА ЗАВЕРШЕНА")
    print("=" * 60)

    return all_chunks


# Запуск при выполнении файла напрямую
if __name__ == "__main__":
    # Обрабатываем все документы из data/raw
    chunks = process_all_documents()

    # Выводим пример первого чанка
    if chunks:
        print("\n📝 Пример первого чанка:")
        print(f"Источник: {chunks[0]['source']}")
        print(f"Текст: {chunks[0]['text'][:300]}...")