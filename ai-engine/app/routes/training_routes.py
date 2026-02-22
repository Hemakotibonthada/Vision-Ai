"""
Vision-AI Training Routes
"""
import os
import uuid
import shutil
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db, AIModel, TrainingRun, Dataset, DatasetImage
from app.services.training_service import training_service
from app.config import settings

router = APIRouter(prefix="/training", tags=["Training"])


@router.post("/start")
async def start_training(
    config: dict = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Start model training with configuration."""
    if training_service.active_training:
        raise HTTPException(status_code=409, detail="Training already in progress")
    
    # Create training run record
    training_run = TrainingRun(
        epochs=config.get("epochs", settings.EPOCHS),
        batch_size=config.get("batch_size", settings.BATCH_SIZE),
        learning_rate=config.get("learning_rate", settings.LEARNING_RATE),
        config=config,
        status="pending",
        started_at=datetime.utcnow()
    )
    db.add(training_run)
    await db.commit()
    await db.refresh(training_run)
    
    # Start training asynchronously
    import asyncio
    asyncio.create_task(training_service.train_yolo(config))
    
    return {
        "training_id": training_run.id,
        "status": "started",
        "config": config
    }


@router.post("/transfer-learn")
async def transfer_learning(
    base_model: str = Query(...),
    data_yaml: str = Query(...),
    freeze_layers: int = Query(10),
    epochs: int = Query(50)
):
    """Transfer learning from pre-trained model."""
    result = await training_service.transfer_learn(base_model, data_yaml, freeze_layers, epochs)
    return result


@router.post("/self-train")
async def self_training(
    model_path: str = Query(...),
    unlabeled_dir: str = Query(...),
    confidence: float = Query(0.9),
    iterations: int = Query(3)
):
    """Self-training with pseudo-labels."""
    result = await training_service.self_train(model_path, unlabeled_dir, confidence, iterations)
    return result


@router.post("/active-learn")
async def active_learning(
    model_path: str = Query(...),
    image_dir: str = Query(...),
    n_samples: int = Query(50),
    strategy: str = Query("uncertainty")
):
    """Select most informative samples for annotation."""
    samples = await training_service.active_learning_select(model_path, image_dir, n_samples, strategy)
    return {"selected_samples": samples, "count": len(samples), "strategy": strategy}


@router.post("/compress")
async def compress_model(
    model_path: str = Query(...),
    method: str = Query("quantize")
):
    """Compress/optimize model for edge deployment."""
    result = await training_service.compress_model(model_path, method)
    return result


@router.post("/tune")
async def tune_hyperparameters(
    data_yaml: str = Query(...),
    param_grid: dict = Body(None)
):
    """Hyperparameter tuning."""
    result = await training_service.tune_hyperparameters(data_yaml, param_grid)
    return result


@router.post("/augment")
async def augment_dataset(
    image_dir: str = Query(...),
    output_dir: str = Query(None),
    copies: int = Query(3),
    augmentations: dict = Body(None)
):
    """Augment dataset with transformations."""
    if not output_dir:
        output_dir = image_dir + "_augmented"
    result = await training_service.augment_dataset(image_dir, output_dir, augmentations, copies)
    return result


@router.get("/status")
async def get_training_status(training_id: str = Query(None)):
    """Get training status."""
    return training_service.get_training_status(training_id)


@router.get("/history")
async def get_training_history(db: AsyncSession = Depends(get_db)):
    """Get training history from database."""
    from sqlalchemy import select, desc
    result = await db.execute(
        select(TrainingRun).order_by(desc(TrainingRun.created_at)).limit(50)
    )
    runs = result.scalars().all()
    return [{
        "id": r.id,
        "status": r.status,
        "epochs": r.epochs,
        "current_epoch": r.current_epoch,
        "train_loss": r.train_loss,
        "val_loss": r.val_loss,
        "best_accuracy": r.best_accuracy,
        "best_mAP": r.best_mAP,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "error_message": r.error_message
    } for r in runs]


# ---- Dataset Management ----

@router.post("/datasets")
async def create_dataset(
    name: str = Query(...),
    description: str = Query(""),
    db: AsyncSession = Depends(get_db)
):
    """Create a new dataset."""
    dataset_path = os.path.join(settings.DATASET_DIR, name)
    os.makedirs(dataset_path, exist_ok=True)
    os.makedirs(os.path.join(dataset_path, "images", "train"), exist_ok=True)
    os.makedirs(os.path.join(dataset_path, "images", "val"), exist_ok=True)
    os.makedirs(os.path.join(dataset_path, "labels", "train"), exist_ok=True)
    os.makedirs(os.path.join(dataset_path, "labels", "val"), exist_ok=True)
    
    dataset = Dataset(name=name, description=description, path=dataset_path)
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    
    return {"id": dataset.id, "name": name, "path": dataset_path}


@router.post("/datasets/{dataset_id}/upload")
async def upload_to_dataset(
    dataset_id: int,
    files: list[UploadFile] = File(...),
    split: str = Query("train"),
    labels: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload images to dataset."""
    from sqlalchemy import select
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    uploaded = []
    for file in files:
        file_path = os.path.join(dataset.path, "images", split, file.filename)
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Get image dimensions
        import cv2
        import numpy as np
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        h, w = img.shape[:2] if img is not None else (0, 0)
        
        db_image = DatasetImage(
            dataset_id=dataset_id,
            file_path=file_path,
            file_name=file.filename,
            width=w, height=h,
            file_size=len(content),
            split=split,
            source="upload"
        )
        db.add(db_image)
        uploaded.append(file.filename)
    
    dataset.total_images = (dataset.total_images or 0) + len(uploaded)
    if split == "train":
        dataset.train_count = (dataset.train_count or 0) + len(uploaded)
    elif split == "val":
        dataset.val_count = (dataset.val_count or 0) + len(uploaded)
    
    await db.commit()
    
    return {"uploaded": len(uploaded), "files": uploaded}


@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """List all datasets."""
    from sqlalchemy import select
    result = await db.execute(select(Dataset))
    datasets = result.scalars().all()
    return [{
        "id": d.id, "name": d.name, "description": d.description,
        "total_images": d.total_images, "train_count": d.train_count,
        "val_count": d.val_count, "classes": d.classes,
        "created_at": d.created_at.isoformat() if d.created_at else None
    } for d in datasets]


# ---- Model Management ----

@router.get("/models")
async def list_ai_models(db: AsyncSession = Depends(get_db)):
    """List all AI models."""
    from sqlalchemy import select
    result = await db.execute(select(AIModel))
    models = result.scalars().all()
    return [{
        "id": m.id, "name": m.name, "type": m.model_type,
        "version": m.version, "accuracy": m.accuracy,
        "mAP": m.mAP, "f1_score": m.f1_score,
        "is_active": m.is_active, "status": m.status,
        "classes": m.classes,
        "created_at": m.created_at.isoformat() if m.created_at else None
    } for m in models]


@router.post("/models")
async def register_model(
    name: str = Query(...),
    model_type: str = Query("yolov8"),
    file_path: str = Query(...),
    classes: list = Body(None),
    db: AsyncSession = Depends(get_db)
):
    """Register a trained model."""
    model = AIModel(
        name=name, model_type=model_type, file_path=file_path,
        classes=classes, status="ready"
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return {"id": model.id, "name": name, "status": "registered"}
