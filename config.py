"""
Central configuration.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv
from core.exceptions import ValidationError

load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    user: str = os.getenv("DB_USER", "root")
    password: str = os.getenv("DB_PASSWORD", "")
    database: str = os.getenv("DB_NAME", "blind_assist_db")
    pool_name: str = "blind_assist_pool"
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "5"))

    def validate(self):
        if not self.password:
            raise ValidationError(
                "DB_PASSWORD is not set. Create a .env file or edit config.py."
            )


@dataclass(frozen=True)
class ModelConfig:
    yolo_model_path: str = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    embedding_model_name: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.45"))
    openfda_timeout: int = int(os.getenv("OPENFDA_TIMEOUT", "3"))
    openfda_enabled: bool = os.getenv("OPENFDA_ENABLED", "True").lower() == "true"


@dataclass(frozen=True)
class AppConfig:
    app_name: str = os.getenv("APP_NAME", "Sight Assist")
    camera_index: int = int(os.getenv("CAMERA_INDEX", "0"))
    camera_width: int = int(os.getenv("CAMERA_WIDTH", "1920"))
    camera_height: int = int(os.getenv("CAMERA_HEIGHT", "1080"))
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"





DB_CONFIG = DatabaseConfig()
MODEL_CONFIG = ModelConfig()
APP_CONFIG = AppConfig()