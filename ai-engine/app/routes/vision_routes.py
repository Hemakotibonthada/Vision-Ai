"""
Vision-AI Advanced Vision Routes
Features 1-25: All new vision and intelligence API endpoints
"""
import io
import base64
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from loguru import logger

router = APIRouter(prefix="/vision", tags=["Advanced Vision"])


def _decode_image(image_bytes: bytes) -> np.ndarray:
    """Decode uploaded image bytes to numpy array."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image")
    return frame


def _encode_image(frame: np.ndarray) -> str:
    """Encode numpy frame to base64 JPEG."""
    _, jpeg = cv2.imencode('.jpg', frame)
    return base64.b64encode(jpeg.tobytes()).decode('utf-8')


# ========== Features 1-5: Anomaly Detection ==========

@router.post("/anomaly/zscore")
async def detect_anomaly_zscore(metric: str = Form(...), value: float = Form(...)):
    """Feature 1: Z-Score anomaly detection."""
    from app.services.anomaly_service import anomaly_detector
    return anomaly_detector.detect_zscore(metric, value)


@router.post("/anomaly/iqr")
async def detect_anomaly_iqr(metric: str = Form(...), values: str = Form(...)):
    """Feature 2: IQR outlier detection."""
    from app.services.anomaly_service import anomaly_detector
    vals = [float(v.strip()) for v in values.split(",")]
    return anomaly_detector.detect_iqr(metric, vals)


@router.post("/anomaly/moving-average")
async def detect_moving_average(metric: str = Form(...), value: float = Form(...),
                                 window: int = Form(50)):
    """Feature 3: Moving average deviation detection."""
    from app.services.anomaly_service import anomaly_detector
    return anomaly_detector.detect_moving_average(metric, value, window)


@router.post("/anomaly/baseline/learn")
async def learn_baseline(metric: str = Form(...), values: str = Form(...)):
    """Feature 4: Learn normal baseline patterns."""
    from app.services.anomaly_service import anomaly_detector
    vals = [float(v.strip()) for v in values.split(",")]
    return anomaly_detector.learn_baseline(metric, vals)


@router.post("/anomaly/correlation")
async def detect_correlation_anomaly(metrics: dict):
    """Feature 5: Multi-metric correlation anomaly."""
    from app.services.anomaly_service import anomaly_detector
    return anomaly_detector.detect_correlation_anomaly(metrics)


@router.get("/anomaly/history")
async def get_anomaly_history(limit: int = Query(100)):
    from app.services.anomaly_service import anomaly_detector
    return {"history": anomaly_detector.get_history(limit), "baselines": anomaly_detector.get_baselines()}


# ========== Feature 6: Gesture Recognition ==========

@router.post("/gesture/detect")
async def detect_gestures(file: UploadFile = File(...)):
    """Feature 6: Detect hand gestures in image."""
    from app.services.vision_services import gesture_service
    frame = _decode_image(await file.read())
    return gesture_service.detect_gestures(frame)


@router.post("/gesture/commands")
async def set_gesture_command(gesture: str = Form(...), command: str = Form(...)):
    """Map a gesture to a command."""
    from app.services.vision_services import gesture_service
    gesture_service.register_gesture_command(gesture, command)
    return {"status": "registered", "gesture": gesture, "command": command}


@router.get("/gesture/commands")
async def get_gesture_commands():
    from app.services.vision_services import gesture_service
    return gesture_service.get_gesture_commands()


# ========== Feature 7: Emotion Detection ==========

@router.post("/emotion/detect")
async def detect_emotions(file: UploadFile = File(...)):
    """Feature 7: Analyze facial emotions."""
    from app.services.vision_services import emotion_service
    frame = _decode_image(await file.read())
    return emotion_service.detect_emotions(frame)


@router.get("/emotion/mood-summary")
async def get_mood_summary(hours: int = Query(24)):
    """Get aggregated mood distribution."""
    from app.services.vision_services import emotion_service
    return emotion_service.get_mood_summary(hours)


# ========== Feature 8: Scene Classification ==========

@router.post("/scene/classify")
async def classify_scene(file: UploadFile = File(...)):
    """Feature 8: Classify scene/environment type."""
    from app.services.vision_services import scene_service
    frame = _decode_image(await file.read())
    return scene_service.classify_scene(frame)


# ========== Feature 9: OCR / Text Extraction ==========

@router.post("/ocr/extract")
async def extract_text(file: UploadFile = File(...)):
    """Feature 9: Extract text regions from image."""
    from app.services.vision_services import ocr_service
    frame = _decode_image(await file.read())
    return ocr_service.extract_text(frame)


# ========== Feature 10: Color Analysis ==========

@router.post("/color/analyze")
async def analyze_colors(file: UploadFile = File(...), k: int = Form(5)):
    """Feature 10: Extract dominant colors."""
    from app.services.vision_services import color_service
    frame = _decode_image(await file.read())
    return color_service.analyze_colors(frame, k)


# ========== Feature 11: Image Quality Assessment ==========

@router.post("/quality/assess")
async def assess_quality(file: UploadFile = File(...)):
    """Feature 11: Image quality assessment (blur, noise, exposure)."""
    from app.services.vision_services import quality_service
    frame = _decode_image(await file.read())
    return quality_service.assess_quality(frame)


# ========== Feature 12: Crowd Counting ==========

@router.post("/crowd/estimate")
async def estimate_crowd(file: UploadFile = File(...)):
    """Feature 12: Crowd density estimation."""
    from app.services.vision_services import crowd_service
    frame = _decode_image(await file.read())
    return crowd_service.estimate_crowd(frame)


# ========== Feature 13-14: Safety Detection ==========

@router.post("/safety/fire-smoke")
async def detect_fire_smoke(file: UploadFile = File(...)):
    """Feature 13: Fire/smoke detection."""
    from app.services.vision_services import safety_service
    frame = _decode_image(await file.read())
    return safety_service.detect_fire_smoke(frame)


@router.post("/safety/ppe")
async def detect_ppe(file: UploadFile = File(...)):
    """Feature 14: PPE (Personal Protective Equipment) detection."""
    from app.services.vision_services import safety_service
    frame = _decode_image(await file.read())
    return safety_service.detect_ppe(frame)


# ========== Feature 15: Motion Analysis ==========

@router.post("/motion/detect")
async def detect_motion(file: UploadFile = File(...), threshold: int = Form(25)):
    """Feature 15: Motion detection with region analysis."""
    from app.services.vision_services import motion_service
    frame = _decode_image(await file.read())
    return motion_service.detect_motion(frame, threshold)


@router.post("/motion/optical-flow")
async def compute_optical_flow(file: UploadFile = File(...)):
    """Motion direction analysis via optical flow."""
    from app.services.vision_services import motion_service
    frame = _decode_image(await file.read())
    return motion_service.compute_optical_flow(frame)


# ========== Feature 16: Privacy Masking ==========

@router.post("/privacy/mask")
async def apply_privacy_mask(file: UploadFile = File(...),
                              blur_faces: bool = Form(True)):
    """Feature 16: Auto-blur faces and sensitive areas."""
    from app.services.intelligence_services import privacy_service
    frame = _decode_image(await file.read())
    result = privacy_service.apply_privacy_mask(frame, blur_faces=blur_faces)
    masked_b64 = base64.b64encode(result["masked_image"]).decode('utf-8')
    return {
        "masked_image_base64": masked_b64,
        "regions_masked": result["regions_masked"],
        "count": result["count"],
        "inference_ms": result["inference_ms"]
    }


# ========== Feature 17: Image Enhancement ==========

@router.post("/enhance/auto")
async def auto_enhance(file: UploadFile = File(...)):
    """Feature 17: Auto-enhance image quality."""
    from app.services.intelligence_services import enhancement_service
    frame = _decode_image(await file.read())
    result = enhancement_service.auto_enhance(frame)
    enhanced_b64 = base64.b64encode(result["enhanced_image"]).decode('utf-8')
    return {
        "enhanced_image_base64": enhanced_b64,
        "operations": result["operations_applied"],
        "original_brightness": result["original_brightness"],
        "enhanced_brightness": result["enhanced_brightness"],
        "inference_ms": result["inference_ms"]
    }


@router.post("/enhance/style")
async def apply_style(file: UploadFile = File(...), style: str = Form("vivid")):
    """Apply artistic style preset to image."""
    from app.services.intelligence_services import enhancement_service
    frame = _decode_image(await file.read())
    result = enhancement_service.apply_style(frame, style)
    styled_b64 = base64.b64encode(result["styled_image"]).decode('utf-8')
    return {"styled_image_base64": styled_b64, "style": style, "inference_ms": result["inference_ms"]}


# ========== Feature 18: Model Ensemble ==========

@router.post("/ensemble/predict")
async def ensemble_predict(file: UploadFile = File(...), strategy: str = Form("voting")):
    """Feature 18: Multi-model ensemble prediction."""
    from app.services.intelligence_services import ensemble_service
    frame = _decode_image(await file.read())
    return ensemble_service.ensemble_predict(frame, strategy)


@router.get("/ensemble/models")
async def list_ensemble_models():
    from app.services.intelligence_services import ensemble_service
    return {"models": list(ensemble_service.models.keys())}


# ========== Feature 19: Notification Templates ==========

@router.post("/notifications/render")
async def render_notification(template_name: str = Form(...), variables: str = Form("{}")):
    """Feature 19: Render notification template."""
    import json
    from app.services.intelligence_services import notification_template_service
    vars_dict = json.loads(variables)
    return notification_template_service.render(template_name, vars_dict)


@router.get("/notifications/templates")
async def list_notification_templates():
    from app.services.intelligence_services import notification_template_service
    return notification_template_service.list_templates()


@router.post("/notifications/templates")
async def create_notification_template(name: str = Form(...), title: str = Form(...),
                                        body: str = Form(...), severity: str = Form("info"),
                                        channels: str = Form("email")):
    from app.services.intelligence_services import notification_template_service
    template = {"title": title, "body": body, "severity": severity, "channels": channels.split(",")}
    notification_template_service.add_template(name, template)
    return {"status": "created", "name": name}


# ========== Feature 20: License Plate Detection ==========

@router.post("/lpr/detect")
async def detect_license_plates(file: UploadFile = File(...)):
    """Feature 20: License plate detection."""
    from app.services.intelligence_services import license_plate_service
    frame = _decode_image(await file.read())
    return license_plate_service.detect_plates(frame)


# ========== Feature 21: Person Re-identification ==========

@router.post("/person-reid/register")
async def register_person(file: UploadFile = File(...), person_id: str = Form(...),
                           x: int = Form(0), y: int = Form(0),
                           w: int = Form(0), h: int = Form(0)):
    """Feature 21: Register a person for re-identification."""
    from app.services.intelligence_services import person_reid_service
    frame = _decode_image(await file.read())
    if w == 0 or h == 0:
        bbox = [0, 0, frame.shape[1], frame.shape[0]]
    else:
        bbox = [x, y, w, h]
    descriptor = person_reid_service.extract_appearance(frame, bbox)
    person_reid_service.register_person(person_id, descriptor)
    return {"status": "registered", "person_id": person_id}


@router.post("/person-reid/identify")
async def identify_person(file: UploadFile = File(...),
                           x: int = Form(0), y: int = Form(0),
                           w: int = Form(0), h: int = Form(0)):
    from app.services.intelligence_services import person_reid_service
    frame = _decode_image(await file.read())
    if w == 0 or h == 0:
        bbox = [0, 0, frame.shape[1], frame.shape[0]]
    else:
        bbox = [x, y, w, h]
    descriptor = person_reid_service.extract_appearance(frame, bbox)
    return person_reid_service.identify_person(descriptor)


# ========== Feature 22: Activity Recognition ==========

@router.post("/activity/classify")
async def classify_activity(file: UploadFile = File(...)):
    """Feature 22: Classify human activity."""
    from app.services.intelligence_services import activity_service
    frame = _decode_image(await file.read())
    return activity_service.classify_activity(frame)


# ========== Feature 23: Package Detection ==========

@router.post("/package/detect")
async def detect_package(file: UploadFile = File(...)):
    """Feature 23: Detect packages/deliveries."""
    from app.services.intelligence_services import package_service
    frame = _decode_image(await file.read())
    return package_service.detect_package(frame)


@router.post("/package/baseline")
async def set_package_baseline(file: UploadFile = File(...)):
    from app.services.intelligence_services import package_service
    frame = _decode_image(await file.read())
    package_service.set_baseline(frame)
    return {"status": "baseline_set"}


# ========== Feature 24: Abandoned Object Detection ==========

@router.post("/abandoned/detect")
async def detect_abandoned(file: UploadFile = File(...)):
    """Feature 24: Detect abandoned/unattended objects."""
    from app.services.intelligence_services import abandoned_object_service
    frame = _decode_image(await file.read())
    return abandoned_object_service.update_and_detect(frame)


# ========== Feature 25: Vehicle Classification ==========

@router.post("/vehicle/classify")
async def classify_vehicle(file: UploadFile = File(...),
                            x: int = Form(0), y: int = Form(0),
                            w: int = Form(0), h: int = Form(0)):
    """Feature 25: Classify vehicle type."""
    from app.services.intelligence_services import vehicle_service
    frame = _decode_image(await file.read())
    bbox = [x, y, w, h] if w > 0 and h > 0 else None
    return vehicle_service.classify_vehicle(frame, bbox)
