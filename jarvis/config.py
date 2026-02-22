"""
Jarvis AI - Configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List


class JarvisSettings(BaseSettings):
    """Jarvis AI Configuration."""

    # ---- Identity ----
    JARVIS_NAME: str = "Jarvis"
    OWNER_NAME: str = "Sir"
    WAKE_WORD: str = "jarvis"

    # ---- Paths ----
    BASE_DIR: str = str(Path(__file__).parent)
    DATA_DIR: str = "./jarvis_data"
    FACE_DB_DIR: str = "./jarvis_data/faces"
    INTRUDER_DIR: str = "./jarvis_data/intruders"
    RECORDINGS_DIR: str = "./jarvis_data/recordings"
    LOGS_DIR: str = "./jarvis_data/logs"
    LEARNING_DIR: str = "./jarvis_data/learning"
    MODELS_DIR: str = "./jarvis_data/models"

    # ---- Face Recognition ----
    FACE_RECOGNITION_MODEL: str = "hog"  # hog (fast) or cnn (accurate)
    FACE_ENCODING_TOLERANCE: float = 0.5  # Lower = stricter matching
    FACE_DETECTION_SCALE: float = 0.25  # Downscale for speed
    MIN_FACE_CONFIDENCE: float = 0.6
    FACE_REGISTRATION_SAMPLES: int = 10  # Number of face samples to register

    # ---- Camera ----
    CAMERA_INDEX: int = 0
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480
    CAMERA_FPS: int = 30
    ESP32_CAM_URL: str = "http://192.168.1.101/capture"

    # ---- Voice ----
    TTS_ENGINE: str = "pyttsx3"  # pyttsx3 (offline) or gtts (online)
    TTS_RATE: int = 175
    TTS_VOLUME: float = 0.9
    STT_ENGINE: str = "vosk"  # vosk (offline) or google (online)
    VOSK_MODEL_PATH: str = "./jarvis_data/models/vosk-model-small-en-us-0.15"
    LISTEN_TIMEOUT: int = 5
    PHRASE_TIMEOUT: int = 10
    ENERGY_THRESHOLD: int = 300

    # ---- State Machine ----
    IDLE_TIMEOUT_SECONDS: int = 300  # 5 min without detection -> sleep
    PRESENCE_CHECK_INTERVAL: int = 2  # seconds between presence checks
    INTRUDER_CAPTURE_INTERVAL: int = 5  # seconds between intruder snapshots
    GREETING_COOLDOWN: int = 1800  # 30 min before re-greeting owner

    # ---- Vision AI Integration ----
    VISION_API_URL: str = "http://localhost:8000"
    VISION_WS_URL: str = "ws://localhost:8000/ws/jarvis"

    # ---- ESP32 Integration ----
    ESP32_SERVER_URL: str = "http://192.168.1.100"
    ESP32_API_PREFIX: str = "/api/v1"
    ESP32_CAM_URL: str = "http://192.168.1.102"
    ESP32_CAM_STREAM_PORT: int = 81
    MQTT_BROKER: str = "127.0.0.1"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CLIENT_ID: str = "jarvis-bridge"

    # ---- MQTT Topics ----
    MQTT_TOPIC_PREFIX: str = "vision-ai/"
    MQTT_JARVIS_CMD: str = "vision-ai/jarvis/cmd"
    MQTT_JARVIS_STATE: str = "vision-ai/jarvis/state"
    MQTT_JARVIS_EVENT: str = "vision-ai/jarvis/event"
    MQTT_CAM_CMD: str = "vision-ai/jarvis/camera/cmd"

    # ---- Security ----
    MAX_INTRUDER_PHOTOS: int = 100
    ALERT_ON_UNKNOWN: bool = True
    RECORD_INTRUDER_VIDEO: bool = True
    INTRUDER_RECORD_DURATION: int = 30  # seconds

    # ---- Learning ----
    LEARNING_ENABLED: bool = True
    CONTEXT_MEMORY_SIZE: int = 1000
    HABIT_TRACKING: bool = True
    EMOTION_DETECTION: bool = True

    # ---- Server ----
    JARVIS_HOST: str = "0.0.0.0"
    JARVIS_PORT: int = 8100
    JARVIS_WS_PORT: int = 8101

    class Config:
        env_file = ".env"
        env_prefix = "JARVIS_"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = JarvisSettings()

# Create directories
for d in [settings.DATA_DIR, settings.FACE_DB_DIR, settings.INTRUDER_DIR,
          settings.RECORDINGS_DIR, settings.LOGS_DIR, settings.LEARNING_DIR,
          settings.MODELS_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)
