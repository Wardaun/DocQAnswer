"""
Модуль для извлечения ответов из текста с помощью русскоязычной BERT (fine-tuned на SberQuAD)
"""

import torch
from transformers import pipeline, AutoModelForQuestionAnswering, AutoTokenizer
from pathlib import Path
import sys
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import settings


class BERTSquadReader:
    """
    Извлекает ответы на русские вопросы используя предобученную модель Den4ikAI/rubert_large_squad_2
    """

    def __init__(self, model_name: str = None, device: str = None):
        if model_name is None:
            model_name = settings.READER_MODEL

        print(f"\n🤖 Инициализация русского BERT Reader")
        print(f"   Модель: {model_name}")

        # Автоопределение устройства
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"   Устройство: {device}")

        # Загрузка модели и токенизатора
        print("   Загрузка модели (около 700 МБ, может занять 2-3 минуты)...")
        self.model = AutoModelForQuestionAnswering.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model.to(device)
        self.device = device

        # Создаём pipeline для удобства
        self.qa_pipeline = pipeline(
            "question-answering",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if device == 'cuda' else -1
        )

        print(f"✅ BERT Reader готов (русская модель)")

    def answer_from_chunk(self, question: str, context: str) -> Dict[str, Any]:
        """
        Извлекает ответ из одного чанка текста
        """
        if not context or len(context.strip()) < 10:
            return {
                "answer": "",
                "confidence": 0.0,
                "start": -1,
                "end": -1,
                "found": False
            }

        # Ограничиваем длину контекста для производительности
        max_context_len = 512
        if len(context) > max_context_len:
            context = context[:max_context_len]

        try:
            result = self.qa_pipeline(
                question=question,
                context=context,
                handle_impossible_answer=True,
                max_answer_len=50
            )

            # Порог уверенности можно позже подстроить
            if result['answer'] and result['score'] > 0.01:
                return {
                    "answer": result['answer'].strip(),
                    "confidence": result['score'],
                    "start": result['start'],
                    "end": result['end'],
                    "found": True
                }
            else:
                return {
                    "answer": "",
                    "confidence": 0.0,
                    "start": -1,
                    "end": -1,
                    "found": False
                }
        except Exception as e:
            print(f"   ⚠️ Ошибка при обработке: {e}")
            return {
                "answer": "",
                "confidence": 0.0,
                "start": -1,
                "end": -1,
                "found": False
            }

    def best_answer_from_chunks(self, question: str, chunks: list) -> Dict[str, Any]:
        """
        Находит лучший ответ среди нескольких чанков
        """
        best_result = None
        best_score = -1

        for i, chunk in enumerate(chunks):
            print(f"   Обработка чанка {i + 1}/{len(chunks)}: {chunk['source']}")
            result = self.answer_from_chunk(question, chunk['text'])
            print(
                f"      Найдено: {result['found']}, ответ: {result.get('answer', '')[:50]}, уверенность: {result['confidence']:.3f}")

            if result['found'] and result['confidence'] > best_score:
                best_score = result['confidence']
                best_result = {
                    "answer": result['answer'],
                    "confidence": result['confidence'],
                    "source": chunk['source'],
                    "chunk_text": chunk['text'],
                    "chunk_id": chunk.get('id', 'unknown')
                }

        print(f"\n📊 Лучший результат: уверенность={best_score:.3f}, найден={best_result is not None}")

        if best_result and best_result['confidence'] >= settings.CONFIDENCE_THRESHOLD:
            print(f"✅ Ответ принят (порог {settings.CONFIDENCE_THRESHOLD})")
            return best_result
        else:
            print(f"❌ Ответ отклонён (порог {settings.CONFIDENCE_THRESHOLD})")
            return {
                "answer": "",
                "confidence": best_result['confidence'] if best_result else 0.0,
                "source": None,
                "chunk_text": None,
                "found": False
            }


# Простой тест при запуске файла
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 ТЕСТ РУССКОГО BERT READER")
    print("="*60)

    test_question = "Как подключить датчик?"
    test_context = """
    Инструкция по настройке датчика температуры ДТ-42.
    Для подключения датчика выполните следующие шаги:
    1. Убедитесь, что питание отключено.
    2. Подключите датчик к контроллеру через разъем X7.
    3. Установите переключатель S1 в положение "A".
    """

    try:
        reader = BERTSquadReader()
        result = reader.answer_from_chunk(test_question, test_context)

        if result['found']:
            print(f"\n✅ Найден ответ:")
            print(f"   Ответ: {result['answer']}")
            print(f"   Уверенность: {result['confidence']:.3f}")
        else:
            print("\n❌ Ответ не найден")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()