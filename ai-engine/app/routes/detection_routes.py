"""
Vision-AI Detection Routes
"""
import io
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db, Detection
from app.services.detection_service import detection_service
from app.services.alert_service import alert_service

router = APIRouter(prefix="/detect", tags=["Detection"])


@router.post("/")
async def detect_objects(
    file: UploadFile = File(...),
    model: Optional[str] = Query(None, description="Model name"),
    confidence: Optional[float] = Query(None, ge=0.1, le=1.0),
    nms: Optional[float] = Query(None, ge=0.1, le=1.0),
    db: AsyncSession = Depends(get_db)
):
    """Run object detection on uploaded image."""
    image_bytes = await file.read()
    
    result = await detection_service.detect(image_bytes, model, confidence, nms)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Save to database
    detection = Detection(
        model_id=None,
        device_id="api",
        image_path=f"uploads/{uuid.uuid4().hex}.jpg",
        results=result["detections"],
        total_objects=result["total_objects"],
        classes_detected=result["classes_detected"],
        inference_time_ms=result["inference_time_ms"],
        image_width=result["image_size"]["width"],
        image_height=result["image_size"]["height"],
        confidence_avg=sum(d["confidence"] for d in result["detections"]) / max(len(result["detections"]), 1)
    )
    db.add(detection)
    await db.commit()
    
    # Evaluate alert rules
    await alert_service.evaluate({
        "type": "detection",
        "total_objects": result["total_objects"],
        "classes": result["classes_detected"],
        "confidence_avg": detection.confidence_avg
    })
    
    return result


@router.post("/batch")
async def detect_batch(
    files: list[UploadFile] = File(...),
    model: Optional[str] = Query(None),
    confidence: Optional[float] = Query(None, ge=0.1, le=1.0),
    db: AsyncSession = Depends(get_db)
):
    """Run detection on multiple images."""
    results = []
    for file in files:
        image_bytes = await file.read()
        result = await detection_service.detect(image_bytes, model, confidence)
        result["filename"] = file.filename
        results.append(result)
    
    return {
        "total_files": len(files),
        "results": results,
        "total_objects": sum(r.get("total_objects", 0) for r in results)
    }


@router.post("/count")
async def count_objects(
    file: UploadFile = File(...),
    target_class: Optional[str] = Query(None, description="Class to count")
):
    """Count objects in image."""
    image_bytes = await file.read()
    return await detection_service.count_objects(image_bytes, target_class)


@router.post("/track")
async def track_objects(file: UploadFile = File(...)):
    """Track objects with persistent IDs."""
    image_bytes = await file.read()
    return await detection_service.track_objects(image_bytes)


@router.post("/features")
async def extract_features(file: UploadFile = File(...)):
    """Extract feature vectors from image."""
    image_bytes = await file.read()
    return await detection_service.extract_features(image_bytes)


@router.post("/heatmap")
async def generate_heatmap(
    file: UploadFile = File(...),
    width: int = Query(640),
    height: int = Query(480)
):
    """Generate detection heatmap."""
    image_bytes = await file.read()
    result = await detection_service.detect(image_bytes)
    heatmap_bytes = await detection_service.generate_heatmap([result], width, height)
    return StreamingResponse(io.BytesIO(heatmap_bytes), media_type="image/jpeg")


@router.post("/gradcam")
async def grad_cam_visualization(
    file: UploadFile = File(...),
    target_class: Optional[int] = Query(None)
):
    """Generate GradCAM visualization."""
    image_bytes = await file.read()
    cam_bytes = await detection_service.grad_cam(image_bytes, target_class)
    return StreamingResponse(io.BytesIO(cam_bytes), media_type="image/jpeg")


@router.get("/models")
async def list_models():
    """List loaded models."""
    stats = detection_service.get_stats()
    return [{"name": m, "type": "YOLO", "active": m == stats.get("active_model")} for m in stats.get("loaded_models", [])]


@router.post("/models/load")
async def load_model(model_name: str = Query(...)):
    """Load a detection model."""
    success = await detection_service.load_yolo_model(model_name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to load model")
    return {"status": "loaded", "model": model_name}


@router.get("/stats")
async def get_detection_stats():
    """Get detection service statistics."""
    return detection_service.get_stats()


@router.get("/history")
async def get_detection_history(limit: int = Query(50, le=1000)):
    """Get recent detection history."""
    return detection_service.detection_history[-limit:]
