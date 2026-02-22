"""
Vision-AI Database Models & Connection
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, Index, create_engine
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from app.config import settings

# Engine & Session
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DATABASE_ECHO)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ============================================
# Database Models
# ============================================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="viewer")  # admin, operator, viewer
    is_active = Column(Boolean, default=True)
    preferences = Column(String(2000), default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    activities = relationship("ActivityLog", back_populates="user")


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    device_type = Column(String(50))  # esp32-server, esp32-cam
    ip_address = Column(String(50))
    mac_address = Column(String(50))
    firmware_version = Column(String(50))
    status = Column(String(50), default="offline")
    is_active = Column(Boolean, default=False)
    group_name = Column(String(100))
    location = Column(String(255))
    capabilities = Column(JSON)
    config = Column(JSON)
    last_seen = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="device")
    sensor_data = relationship("SensorData", back_populates="device")


class AIModel(Base):
    __tablename__ = "ai_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    model_type = Column(String(100))  # yolov8, ssd, classification, face
    version = Column(String(50))
    file_path = Column(String(500))
    file_size = Column(Integer)
    accuracy = Column(Float)
    mAP = Column(Float)
    precision_val = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    classes = Column(JSON)
    config = Column(JSON)
    training_config = Column(JSON)
    is_active = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    status = Column(String(50), default="ready")  # ready, training, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    trained_at = Column(DateTime)

    detections = relationship("Detection", back_populates="model")
    training_runs = relationship("TrainingRun", back_populates="model")


class TrainingRun(Base):
    __tablename__ = "training_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("ai_models.id"))
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    epochs = Column(Integer)
    current_epoch = Column(Integer, default=0)
    batch_size = Column(Integer)
    learning_rate = Column(Float)
    train_loss = Column(Float)
    val_loss = Column(Float)
    best_accuracy = Column(Float)
    best_mAP = Column(Float)
    config = Column(JSON)
    metrics_history = Column(JSON)  # [{epoch, loss, accuracy, ...}]
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text)

    model = relationship("AIModel", back_populates="training_runs")
    dataset = relationship("Dataset", back_populates="training_runs")


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    path = Column(String(500))
    total_images = Column(Integer, default=0)
    train_count = Column(Integer, default=0)
    val_count = Column(Integer, default=0)
    test_count = Column(Integer, default=0)
    classes = Column(JSON)
    class_distribution = Column(JSON)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    images = relationship("DatasetImage", back_populates="dataset")
    training_runs = relationship("TrainingRun", back_populates="dataset")


class DatasetImage(Base):
    __tablename__ = "dataset_images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    file_path = Column(String(500))
    file_name = Column(String(255))
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)
    split = Column(String(20))  # train, val, test
    annotations = Column(JSON)
    labels = Column(JSON)
    quality_score = Column(Float)
    is_augmented = Column(Boolean, default=False)
    source = Column(String(100))  # upload, capture, augmented
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="images")


class Detection(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("ai_models.id"))
    device_id = Column(String(100), index=True)
    image_path = Column(String(500))
    results = Column(JSON)  # [{class, confidence, bbox, ...}]
    total_objects = Column(Integer, default=0)
    classes_detected = Column(JSON)
    inference_time_ms = Column(Float)
    image_width = Column(Integer)
    image_height = Column(Integer)
    confidence_avg = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    model = relationship("AIModel", back_populates="detections")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    event_type = Column(String(100), index=True)  # motion, face, alert, detection, system
    severity = Column(Integer, default=1)  # 1=info, 2=warning, 3=critical
    title = Column(String(255))
    description = Column(Text)
    data = Column(JSON)
    image_path = Column(String(500))
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("Device", back_populates="events")


class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    temperature = Column(Float)
    humidity = Column(Float)
    light = Column(Integer)
    motion = Column(Boolean)
    distance = Column(Float)
    battery = Column(Float)
    custom_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("Device", back_populates="sensor_data")


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    event_type = Column(String(100))
    condition = Column(JSON)  # {field: "confidence", op: ">", value: 0.9}
    actions = Column(JSON)  # [{type: "email", target: "..."}, {type: "webhook"}]
    is_active = Column(Boolean, default=True)
    cooldown_seconds = Column(Integer, default=60)
    last_triggered = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Zone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    camera_id = Column(String(100))
    zone_type = Column(String(50))  # intrusion, counting, dwell
    points = Column(JSON)  # [{x, y}, ...]
    color = Column(String(20), default="#ff0000")
    is_active = Column(Boolean, default=True)
    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255))
    resource = Column(String(255))
    details = Column(JSON)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activities")


class SystemConfig(Base):
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text)
    value_type = Column(String(50), default="string")
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
