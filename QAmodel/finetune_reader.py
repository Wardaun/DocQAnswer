"""
Fine-tuning русской BERT модели на собственных данных
"""

import json
import torch
from transformers import (
    AutoModelForQuestionAnswering,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    default_data_collator
)
from datasets import Dataset, DatasetDict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from config.settings import settings


class QADatasetPreprocessor:
    """
    Подготовка данных для fine-tuning вопросно-ответной модели
    """

    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = settings.READER_MODEL

        print(f"🔧 Загрузка токенизатора: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.max_length = 384
        self.doc_stride = 128

    def load_labeled_data(self, json_path: Path) -> list:
        """Загружает размеченные данные из JSON"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Фильтруем только данные с правильными ответами
        labeled_data = [item for item in data if item.get('correct_answer')]
        print(f"📊 Загружено {len(labeled_data)} размеченных примеров")

        return labeled_data

    def prepare_train_features(self, examples):
        """Подготовка признаков для обучения"""

        # Токенизируем вопросы и контексты
        tokenized_examples = self.tokenizer(
            examples["question"],
            examples["context"],
            truncation="only_second",
            max_length=self.max_length,
            stride=self.doc_stride,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            padding="max_length",
        )

        # Маппинг для поиска позиций ответа
        sample_mapping = tokenized_examples.pop("overflow_to_sample_mapping")
        offset_mapping = tokenized_examples.pop("offset_mapping")

        start_positions = []
        end_positions = []

        for i, offsets in enumerate(offset_mapping):
            input_ids = tokenized_examples["input_ids"][i]
            sample_index = sample_mapping[i]
            answer = examples["answer"][sample_index]

            # Ищем ответ в исходном тексте
            start_char = answer["answer_start"][0]
            end_char = start_char + len(answer["text"][0])

            sequence_ids = tokenized_examples.sequence_ids(i)

            # Находим начало и конец ответа в токенах
            token_start_index = 0
            token_end_index = 0

            for idx, (start, end) in enumerate(offsets):
                if sequence_ids[idx] != 1:  # Второй сегмент (контекст)
                    continue
                if start <= start_char and end >= start_char:
                    token_start_index = idx
                if start <= end_char and end >= end_char:
                    token_end_index = idx

            start_positions.append(token_start_index)
            end_positions.append(token_end_index)

        tokenized_examples["start_positions"] = start_positions
        tokenized_examples["end_positions"] = end_positions

        return tokenized_examples

    def convert_to_dataset(self, labeled_data: list, contexts: dict = None) -> Dataset:
        """
        Конвертирует размеченные данные в Dataset для обучения

        Args:
            labeled_data: список с вопросами, ответами и контекстами
            contexts: словарь {source_doc: chunk_text} для получения контекста
        """
        questions = []
        answers = []
        contexts_list = []

        for item in labeled_data:
            questions.append(item["question"])

            # Формируем ответ в нужном формате
            answer_text = item["correct_answer"]

            # Ищем позицию ответа в контексте
            context = item.get("context", "")
            if context:
                answer_start = context.find(answer_text)
                if answer_start == -1:
                    print(f"⚠️ Ответ не найден в контексте: {answer_text[:50]}...")
                    answer_start = 0
            else:
                answer_start = 0

            answers.append({
                "text": [answer_text],
                "answer_start": [answer_start]
            })
            contexts_list.append(context)

        # Создаём Dataset
        data_dict = {
            "question": questions,
            "context": contexts_list,
            "answer": answers,
            "id": [f"train_{i}" for i in range(len(questions))]
        }

        dataset = Dataset.from_dict(data_dict)

        # Применяем предобработку
        dataset = dataset.map(
            self.prepare_train_features,
            batched=True,
            remove_columns=dataset.column_names
        )

        return dataset


def finetune_model(
        train_data_path: Path = Path("data/finetuning/labeled_data.json"),
        output_dir: Path = Path("models/finetuned_reader"),
        model_name: str = None
):
    """
    Основная функция fine-tuning
    """
    print("\n" + "=" * 60)
    print("🔧 FINE-TUNING МОДЕЛИ")
    print("=" * 60)

    if model_name is None:
        model_name = settings.READER_MODEL

    # 1. Загружаем данные
    preprocessor = QADatasetPreprocessor(model_name)

    if not train_data_path.exists():
        print(f"❌ Файл с данными не найден: {train_data_path}")
        print("   Сначала создайте labeled_data.json с размеченными ответами")
        return None

    labeled_data = preprocessor.load_labeled_data(train_data_path)

    if len(labeled_data) < 10:
        print(f"⚠️ Мало данных для обучения (нужно минимум 10-20 примеров)")
        print(f"   Сейчас: {len(labeled_data)} примеров")
        response = input("   Продолжить? (y/n): ")
        if response.lower() != 'y':
            return None

    # 2. Загружаем модель
    print(f"\n🤖 Загрузка модели: {model_name}")
    model = AutoModelForQuestionAnswering.from_pretrained(model_name)

    # 3. Подготавливаем Dataset
    print("\n📊 Подготовка данных для обучения...")
    # Для простоты используем все данные как тренировочные
    # При большом количестве данных можно разделить на train/val
    dataset = preprocessor.convert_to_dataset(labeled_data)

    # 4. Настройки обучения
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        evaluation_strategy="no",  # Для малых данных не нужна валидация
        learning_rate=3e-5,
        per_device_train_batch_size=4,  # Уменьшить если мало памяти
        per_device_eval_batch_size=4,
        num_train_epochs=3,
        weight_decay=0.01,
        save_total_limit=2,
        save_steps=100,
        logging_steps=50,
        report_to="none",  # Отключаем wandb и т.д.
        fp16=torch.cuda.is_available(),  # Ускорение на GPU
    )

    # 5. Запускаем обучение
    print("\n🚀 Запуск обучения...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=default_data_collator,
        tokenizer=preprocessor.tokenizer,
    )

    trainer.train()

    # 6. Сохраняем модель
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_dir))
    preprocessor.tokenizer.save_pretrained(str(output_dir))

    print(f"\n✅ Модель сохранена в {output_dir}")
    print("\n💡 Чтобы использовать новую модель, обновите в config/settings.py:")
    print(f'   READER_MODEL = "{output_dir}"')

    return model


def create_sample_labeled_data():
    """
    Создаёт пример размеченных данных для тестирования fine-tuning
    """
    sample_data = [
        {
            "query_id": 1,
            "question": "Как настроить датчик температуры?",
            "source_doc": "test_doc.txt",
            "context": "Инструкция по настройке датчика температуры ДТ-42. 1. Убедитесь, что питание отключено. 2. Подключите датчик к контроллеру через разъем X7. 3. Установите переключатель S1 в положение 'A'. 4. Включите питание и дождитесь зеленого индикатора. 5. Если индикатор красный - проверьте полярность подключения.",
            "correct_answer": "Убедитесь, что питание отключено. Подключите датчик к контроллеру через разъем X7. Установите переключатель S1 в положение 'A'. Включите питание и дождитесь зеленого индикатора."
        },
        {
            "query_id": 2,
            "question": "Что делать при красном индикаторе?",
            "source_doc": "test_doc.txt",
            "context": "Инструкция по настройке датчика температуры ДТ-42. 1. Убедитесь, что питание отключено. 2. Подключите датчик к контроллеру через разъем X7. 3. Установите переключатель S1 в положение 'A'. 4. Включите питание и дождитесь зеленого индикатора. 5. Если индикатор красный - проверьте полярность подключения.",
            "correct_answer": "Проверьте полярность подключения"
        }
    ]

    output_file = Path("data/finetuning/labeled_data.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Пример размеченных данных создан: {output_file}")
    print("   Отредактируйте файл, добавив свои вопросы и ответы")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fine-tuning BERT для QA")
    parser.add_argument("--create-sample", action="store_true", help="Создать пример данных")
    parser.add_argument("--train", action="store_true", help="Запустить обучение")
    parser.add_argument("--data", type=str, default="data/finetuning/labeled_data.json", help="Путь к данным")

    args = parser.parse_args()

    if args.create_sample:
        create_sample_labeled_data()
    elif args.train:
        finetune_model(Path(args.data))
    else:
        print("Использование:")
        print("  python finetune_reader.py --create-sample  # Создать пример данных")
        print("  python finetune_reader.py --train           # Запустить обучение")
        print("  python finetune_reader.py --train --data путь/к/data.json")