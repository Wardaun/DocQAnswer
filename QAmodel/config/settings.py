from pathlib import Path

# Корневая директория проекта (где лежит этот файл)
ROOT_DIR = Path(__file__).parent.parent


class Settings:
    # Пути
    DATA_DIR: Path = ROOT_DIR / "data"
    LOGS_DIR: Path = ROOT_DIR / "logs"
    MODELS_DIR: Path = ROOT_DIR / "models"

    # Retriever
    RETRIEVER_MODEL: str = "intfloat/multilingual-e5-large"
    TOP_K_CHUNKS: int = 10

    # Reader
    READER_MODEL: str = "models/finetuned_reader"
    CONFIDENCE_THRESHOLD: float = 0.1

    # Chunking
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 100

    # База данных
    DB_PATH: Path = DATA_DIR / "QAmodel.db"




settings = Settings()
