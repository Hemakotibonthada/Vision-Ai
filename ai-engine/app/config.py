"""
Vision-AI Engine Configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Vision-AI Engine"
    APP_VERSION: str = "2.5.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    SECRET_KEY: str = "vision-ai-secret-key-change-in-production"
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["*"]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/vision_ai.db"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300

    # MQTT
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USER: str = "vision_ai"
    MQTT_PASSWORD: str = "mqtt_pass_2024"
    MQTT_CLIENT_ID: str = "ai-engine-01"
    MQTT_TOPIC_PREFIX: str = "vision-ai/"

    # AI Models
    MODEL_DIR: str = "./models"
    DEFAULT_MODEL: str = "yolov8n"
    CONFIDENCE_THRESHOLD: float = 0.5
    NMS_THRESHOLD: float = 0.45
    MAX_DETECTIONS: int = 100
    DEVICE: str = "auto"  # auto, cpu, cuda

    # Training
    TRAINING_DIR: str = "./training"
    DATASET_DIR: str = "./datasets"
    EPOCHS: int = 100
    BATCH_SIZE: int = 16
    LEARNING_RATE: float = 0.001
    EARLY_STOPPING_PATIENCE: int = 10
    TRAIN_VAL_SPLIT: float = 0.8
    AUGMENTATION_ENABLED: bool = True

    # Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".bmp", ".gif"]

    # Alerts
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_EMAIL: str = ""
    WEBHOOK_URL: str = ""
    SLACK_WEBHOOK: str = ""

    # JWT Auth
    JWT_SECRET: str = "jwt-secret-key-change-this"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/vision_ai.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Create directories
for dir_path in [settings.MODEL_DIR, settings.TRAINING_DIR, settings.DATASET_DIR,
                 settings.UPLOAD_DIR, "./data", "./logs"]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)
