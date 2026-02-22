"""
Vision-AI Intelligence Services
Features 16-25: Privacy masking, image enhancement, model ensemble,
notification templates, license plate detection, person re-identification,
activity recognition, package detection, abandoned object detection, vehicle classification
"""
import cv2
import numpy as np
import time
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from loguru import logger


class PrivacyMaskService:
    """Feature 16: Auto-blur faces and sensitive areas."""

    def __init__(self):
        self.face_cascade = None
        self.privacy_zones = []
        self.mask_count = 0
        self._load()
        logger.info("Privacy Mask Service initialized")

    def _load(self):
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except Exception:
            pass

    def apply_privacy_mask(self, frame: np.ndarray, blur_faces: bool = True,
                           blur_bodies: bool = False, custom_zones: list = None) -> dict:
        """Apply privacy masks (blur) to detected faces and zones."""
        start = time.time()
        result_frame = frame.copy()
        regions_masked = []

        if blur_faces and self.face_cascade:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                roi = result_frame[y:y+h, x:x+w]
                blurred = cv2.GaussianBlur(roi, (99, 99), 30)
                result_frame[y:y+h, x:x+w] = blurred
                regions_masked.append({"type": "face", "bbox": [int(x), int(y), int(w), int(h)]})

        if custom_zones:
            for zone in custom_zones:
                x, y, w, h = zone["x"], zone["y"], zone["w"], zone["h"]
                roi = result_frame[y:y+h, x:x+w]
                blurred = cv2.GaussianBlur(roi, (99, 99), 30)
                result_frame[y:y+h, x:x+w] = blurred
                regions_masked.append({"type": "custom", "bbox": [x, y, w, h]})

        self.mask_count += len(regions_masked)
        _, jpeg = cv2.imencode('.jpg', result_frame)

        return {
            "masked_image": jpeg.tobytes(),
            "regions_masked": regions_masked,
            "count": len(regions_masked),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }

    def add_privacy_zone(self, zone: dict):
        self.privacy_zones.append(zone)

    def get_stats(self) -> dict:
        return {"total_masks_applied": self.mask_count, "privacy_zones": len(self.privacy_zones)}


class ImageEnhancementService:
    """Feature 17: Auto-enhance low quality images."""

    def __init__(self):
        self.enhancement_count = 0
        logger.info("Image Enhancement Service initialized")

    def auto_enhance(self, frame: np.ndarray) -> dict:
        """Automatically enhance image quality."""
        start = time.time()
        enhanced = frame.copy()
        operations = []

        # Brightness/contrast correction
        gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        if mean_brightness < 80:
            alpha = 1.3
            beta = 40
            enhanced = cv2.convertScaleAbs(enhanced, alpha=alpha, beta=beta)
            operations.append("brightness_boost")
        elif mean_brightness > 200:
            alpha = 0.8
            beta = -20
            enhanced = cv2.convertScaleAbs(enhanced, alpha=alpha, beta=beta)
            operations.append("brightness_reduce")

        # Histogram equalization
        lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(l_channel)
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        operations.append("clahe_contrast")

        # Denoising
        noise_level = float(np.std(cv2.absdiff(gray, cv2.GaussianBlur(gray, (5, 5), 0))))
        if noise_level > 15:
            enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
            operations.append("denoising")

        # Sharpening
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        enhanced = cv2.filter2D(enhanced, -1, kernel)
        operations.append("sharpening")

        # White balance
        enhanced = self._auto_white_balance(enhanced)
        operations.append("white_balance")

        self.enhancement_count += 1
        _, jpeg = cv2.imencode('.jpg', enhanced)

        return {
            "enhanced_image": jpeg.tobytes(),
            "operations_applied": operations,
            "original_brightness": round(mean_brightness, 1),
            "enhanced_brightness": round(float(np.mean(cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY))), 1),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _auto_white_balance(self, frame: np.ndarray) -> np.ndarray:
        result = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        avg_a = np.average(result[:, :, 1])
        avg_b = np.average(result[:, :, 2])
        result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
        result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
        return cv2.cvtColor(result, cv2.COLOR_LAB2BGR)

    def apply_style(self, frame: np.ndarray, style: str = "vivid") -> dict:
        """Apply artistic style presets to images."""
        start = time.time()
        if style == "vivid":
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.3, 0, 255).astype(np.uint8)
            result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        elif style == "vintage":
            result = cv2.applyColorMap(frame, cv2.COLORMAP_AUTUMN)
            result = cv2.addWeighted(frame, 0.7, result, 0.3, 0)
        elif style == "noir":
            result = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        elif style == "cool":
            result = frame.copy()
            result[:, :, 0] = np.clip(result[:, :, 0] * 1.1, 0, 255).astype(np.uint8)
            result[:, :, 2] = np.clip(result[:, :, 2] * 0.9, 0, 255).astype(np.uint8)
        elif style == "warm":
            result = frame.copy()
            result[:, :, 0] = np.clip(result[:, :, 0] * 0.9, 0, 255).astype(np.uint8)
            result[:, :, 2] = np.clip(result[:, :, 2] * 1.1, 0, 255).astype(np.uint8)
        else:
            result = frame

        _, jpeg = cv2.imencode('.jpg', result)
        return {
            "styled_image": jpeg.tobytes(),
            "style": style,
            "inference_ms": round((time.time() - start) * 1000, 2)
        }


class ModelEnsembleService:
    """Feature 18: Combine multiple model predictions."""

    def __init__(self):
        self.models = {}
        self.ensemble_history = []
        logger.info("Model Ensemble Service initialized")

    def register_model(self, name: str, model_fn):
        self.models[name] = model_fn

    def ensemble_predict(self, frame: np.ndarray, strategy: str = "voting") -> dict:
        """Combine predictions from multiple models."""
        start = time.time()
        predictions = {}
        for name, fn in self.models.items():
            try:
                predictions[name] = fn(frame)
            except Exception as e:
                predictions[name] = {"error": str(e)}

        if strategy == "voting":
            result = self._majority_voting(predictions)
        elif strategy == "averaging":
            result = self._average_confidence(predictions)
        elif strategy == "stacking":
            result = self._stacking(predictions)
        else:
            result = predictions

        ensemble_result = {
            "strategy": strategy,
            "individual_predictions": predictions,
            "ensemble_result": result,
            "models_used": list(self.models.keys()),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.ensemble_history.append(ensemble_result)
        return ensemble_result

    def _majority_voting(self, predictions: dict) -> dict:
        votes = defaultdict(int)
        for _, pred in predictions.items():
            if isinstance(pred, dict) and "class" in pred:
                votes[pred["class"]] += 1
        if not votes:
            return {"class": "unknown", "votes": 0}
        winner = max(votes, key=votes.get)
        return {"class": winner, "votes": votes[winner], "total_models": len(predictions)}

    def _average_confidence(self, predictions: dict) -> dict:
        confidences = defaultdict(list)
        for _, pred in predictions.items():
            if isinstance(pred, dict) and "detections" in pred:
                for det in pred["detections"]:
                    confidences[det.get("class", "unknown")].append(det.get("confidence", 0))
        averaged = {cls: round(np.mean(confs), 3) for cls, confs in confidences.items()}
        return {"averaged_confidences": averaged}

    def _stacking(self, predictions: dict) -> dict:
        return {"stacked": True, "predictions": predictions}


class NotificationTemplateService:
    """Feature 19: Customizable alert notification templates."""

    def __init__(self):
        self.templates = {
            "intrusion": {
                "title": "Intrusion Alert - {zone}",
                "body": "Motion detected in {zone} at {time}. {count} object(s) detected with {confidence}% confidence.",
                "severity": "critical",
                "channels": ["email", "push", "sms"]
            },
            "fire": {
                "title": "FIRE ALERT - {location}",
                "body": "Potential fire/smoke detected at {location}. Coverage: {coverage}%. Immediate action required!",
                "severity": "critical",
                "channels": ["email", "push", "sms", "alarm"]
            },
            "device_offline": {
                "title": "Device Offline - {device_name}",
                "body": "Device {device_name} ({device_id}) has gone offline. Last seen: {last_seen}.",
                "severity": "warning",
                "channels": ["email", "push"]
            },
            "daily_report": {
                "title": "Daily Activity Report - {date}",
                "body": "Detections: {detection_count}, Events: {event_count}, Avg confidence: {avg_confidence}%.",
                "severity": "info",
                "channels": ["email"]
            },
            "face_recognized": {
                "title": "Person Identified - {person_name}",
                "body": "{person_name} identified at {location} with {confidence}% confidence at {time}.",
                "severity": "info",
                "channels": ["push"]
            },
            "anomaly": {
                "title": "Anomaly Detected - {metric}",
                "body": "Unusual {metric} value: {value} (normal range: {normal_range}). Z-score: {z_score}.",
                "severity": "warning",
                "channels": ["email", "push"]
            }
        }
        logger.info("Notification Template Service initialized")

    def render(self, template_name: str, variables: dict) -> dict:
        """Render a notification template with variables."""
        if template_name not in self.templates:
            return {"error": f"Template '{template_name}' not found"}

        template = self.templates[template_name]
        try:
            title = template["title"].format(**variables)
            body = template["body"].format(**variables)
        except KeyError as e:
            return {"error": f"Missing variable: {e}"}

        return {
            "title": title,
            "body": body,
            "severity": template["severity"],
            "channels": template["channels"],
            "template": template_name,
            "rendered_at": datetime.utcnow().isoformat()
        }

    def add_template(self, name: str, template: dict):
        self.templates[name] = template

    def list_templates(self) -> dict:
        return {name: {k: v for k, v in t.items() if k != "body"} for name, t in self.templates.items()}


class LicensePlateService:
    """Feature 20: License plate detection."""

    def __init__(self):
        self.plate_cascade = None
        self.plate_history = []
        self._load()
        logger.info("License Plate Service initialized")

    def _load(self):
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml'
            self.plate_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            pass

    def detect_plates(self, frame: np.ndarray) -> dict:
        """Detect license plates in image."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        plates = []

        if self.plate_cascade and not self.plate_cascade.empty():
            detected = self.plate_cascade.detectMultiScale(gray, 1.1, 4)
            for (x, y, w, h) in detected:
                plate_roi = gray[y:y+h, x:x+w]
                plates.append({
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "confidence": 0.75,
                    "aspect_ratio": round(w / h, 2) if h > 0 else 0
                })
        else:
            # Fallback: edge-based plate detection
            edges = cv2.Canny(gray, 100, 200)
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect = w / h if h > 0 else 0
                area = w * h
                if 2.0 < aspect < 6.0 and 1000 < area < 50000:
                    plates.append({
                        "bbox": [int(x), int(y), int(w), int(h)],
                        "confidence": 0.5,
                        "aspect_ratio": round(aspect, 2)
                    })

        result = {
            "plates": plates[:10],
            "count": len(plates),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        if plates:
            self.plate_history.append(result)
        return result


class PersonReIdService:
    """Feature 21: Person re-identification across cameras."""

    def __init__(self):
        self.person_registry = {}
        self.tracking_history = []
        logger.info("Person Re-ID Service initialized")

    def extract_appearance(self, frame: np.ndarray, bbox: list) -> np.ndarray:
        """Extract appearance descriptor for a person crop."""
        x, y, w, h = bbox
        x, y = max(0, x), max(0, y)
        crop = frame[y:y+h, x:x+w]
        if crop.size == 0:
            return np.zeros(256)
        resized = cv2.resize(crop, (64, 128))
        hist_features = []
        for ch in range(3):
            hist = cv2.calcHist([resized], [ch], None, [32], [0, 256]).flatten()
            hist = hist / (hist.sum() + 1e-7)
            hist_features.extend(hist)
        
        # Add HOG-like features
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        blocks = [(0, 0, 32, 64), (32, 0, 64, 64), (0, 64, 32, 128), (32, 64, 64, 128)]
        for bx1, by1, bx2, by2 in blocks:
            block = magnitude[by1:by2, bx1:bx2]
            hist_features.extend([float(np.mean(block)), float(np.std(block))])
        
        return np.array(hist_features[:256])

    def register_person(self, person_id: str, descriptor: np.ndarray):
        self.person_registry[person_id] = {
            "descriptor": descriptor,
            "first_seen": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "sightings": 1
        }

    def identify_person(self, descriptor: np.ndarray, threshold: float = 0.7) -> dict:
        """Match a person against registered descriptors."""
        best_match = None
        best_score = 0
        for pid, data in self.person_registry.items():
            score = float(np.dot(descriptor, data["descriptor"]) / 
                         (np.linalg.norm(descriptor) * np.linalg.norm(data["descriptor"]) + 1e-7))
            if score > best_score:
                best_score = score
                best_match = pid

        if best_match and best_score >= threshold:
            self.person_registry[best_match]["last_seen"] = datetime.utcnow().isoformat()
            self.person_registry[best_match]["sightings"] += 1
            return {"matched": True, "person_id": best_match, "similarity": round(best_score, 3)}
        return {"matched": False, "best_score": round(best_score, 3)}


class ActivityRecognitionService:
    """Feature 22: Human activity classification."""

    ACTIVITIES = [
        "standing", "walking", "running", "sitting", "lying_down",
        "waving", "jumping", "bending", "pushing", "pulling",
        "carrying", "talking", "eating", "working", "idle"
    ]

    def __init__(self):
        self.frame_buffer = []
        self.buffer_size = 16
        self.activity_history = []
        logger.info("Activity Recognition Service initialized")

    def classify_activity(self, frame: np.ndarray) -> dict:
        """Classify human activity from frame sequence."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (64, 64))
        self.frame_buffer.append(resized)
        
        if len(self.frame_buffer) > self.buffer_size:
            self.frame_buffer.pop(0)
        
        if len(self.frame_buffer) < 4:
            return {"activity": "unknown", "confidence": 0, "buffer_fill": len(self.frame_buffer) / self.buffer_size}
        
        # Temporal features
        temporal_diff = np.mean([np.mean(np.abs(self.frame_buffer[i].astype(float) - self.frame_buffer[i-1].astype(float))) 
                                 for i in range(1, len(self.frame_buffer))])
        
        # Spatial features
        edges = cv2.Canny(resized, 50, 150)
        edge_density = float(np.sum(edges > 0)) / edges.size
        
        # Vertical vs horizontal motion
        if len(self.frame_buffer) >= 2:
            flow_approx = np.abs(self.frame_buffer[-1].astype(float) - self.frame_buffer[-2].astype(float))
            vertical_motion = float(np.mean(flow_approx[:32, :]) - np.mean(flow_approx[32:, :]))
            horizontal_motion = float(np.mean(flow_approx[:, :32]) - np.mean(flow_approx[:, 32:]))
        else:
            vertical_motion = 0
            horizontal_motion = 0
        
        activity = self._classify_from_features(temporal_diff, edge_density, vertical_motion, horizontal_motion)
        
        result = {
            "activity": activity["name"],
            "confidence": round(activity["confidence"], 3),
            "features": {
                "temporal_diff": round(temporal_diff, 2),
                "edge_density": round(edge_density, 4),
                "vertical_motion": round(vertical_motion, 2),
                "horizontal_motion": round(horizontal_motion, 2)
            },
            "buffer_fill": round(len(self.frame_buffer) / self.buffer_size, 2),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.activity_history.append(result)
        return result

    def _classify_from_features(self, temporal, edge, vert, horiz) -> dict:
        if temporal < 2: return {"name": "standing" if edge > 0.1 else "idle", "confidence": 0.7}
        if temporal < 5: return {"name": "sitting" if vert < 0 else "walking", "confidence": 0.6}
        if temporal < 15: return {"name": "walking", "confidence": 0.65}
        if temporal < 30: return {"name": "running" if abs(horiz) > abs(vert) else "jumping", "confidence": 0.55}
        return {"name": "running", "confidence": 0.5}


class PackageDetectionService:
    """Feature 23: Delivery/package detection at door."""

    def __init__(self):
        self.baseline_frame = None
        self.detection_history = []
        logger.info("Package Detection Service initialized")

    def set_baseline(self, frame: np.ndarray):
        self.baseline_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def detect_package(self, frame: np.ndarray) -> dict:
        """Detect new objects (packages) by comparison to baseline."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.baseline_frame is None:
            self.baseline_frame = gray
            return {"package_detected": False, "message": "Baseline set"}
        
        baseline_resized = cv2.resize(self.baseline_frame, (gray.shape[1], gray.shape[0]))
        diff = cv2.absdiff(baseline_resized, gray)
        thresh = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        packages = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 3000:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect = w / h if h > 0 else 0
                if 0.3 < aspect < 3.0:
                    packages.append({
                        "bbox": [int(x), int(y), int(w), int(h)],
                        "area": int(area),
                        "confidence": min(0.9, area / 50000 + 0.3)
                    })
        
        result = {
            "package_detected": len(packages) > 0,
            "packages": packages[:5],
            "count": len(packages),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        if packages:
            self.detection_history.append(result)
        return result


class AbandonedObjectService:
    """Feature 24: Unattended/abandoned object detection."""

    def __init__(self):
        self.background = None
        self.static_objects = {}
        self.alert_threshold_seconds = 60
        self.alert_history = []
        logger.info("Abandoned Object Detection Service initialized")

    def update_and_detect(self, frame: np.ndarray) -> dict:
        """Detect objects that remain stationary for too long."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.background is None:
            self.background = gray.astype(float)
            return {"abandoned_objects": [], "count": 0}
        
        cv2.accumulateWeighted(gray, self.background, 0.005)
        diff = cv2.absdiff(gray, cv2.convertScaleAbs(self.background))
        thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        current_objects = {}
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 2000:
                x, y, w, h = cv2.boundingRect(cnt)
                key = f"{x//20}_{y//20}"
                current_objects[key] = {"bbox": [int(x), int(y), int(w), int(h)], "area": int(area)}
        
        now = time.time()
        abandoned = []
        for key, obj in current_objects.items():
            if key in self.static_objects:
                duration = now - self.static_objects[key]["first_seen"]
                if duration > self.alert_threshold_seconds:
                    abandoned.append({**obj, "duration_seconds": round(duration, 1), "alert": True})
            else:
                self.static_objects[key] = {"first_seen": now, **obj}
        
        # Clean old entries
        self.static_objects = {k: v for k, v in self.static_objects.items()
                               if k in current_objects or now - v["first_seen"] < 300}
        
        result = {
            "abandoned_objects": abandoned,
            "count": len(abandoned),
            "tracked_objects": len(self.static_objects),
            "alert_threshold_seconds": self.alert_threshold_seconds,
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        if abandoned:
            self.alert_history.append(result)
        return result


class VehicleClassificationService:
    """Feature 25: Vehicle type classification."""

    VEHICLE_TYPES = ["sedan", "suv", "truck", "van", "motorcycle", "bus", "bicycle"]

    def __init__(self):
        self.vehicle_history = []
        logger.info("Vehicle Classification Service initialized")

    def classify_vehicle(self, frame: np.ndarray, bbox: list = None) -> dict:
        """Classify vehicle type from image region."""
        start = time.time()
        if bbox:
            x, y, w, h = bbox
            roi = frame[max(0, y):y+h, max(0, x):x+w]
        else:
            roi = frame
        
        if roi.size == 0:
            return {"vehicle_type": "unknown", "confidence": 0}
        
        resized = cv2.resize(roi, (128, 128))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        h, w = gray.shape
        aspect = w / h if h > 0 else 1
        area_ratio = cv2.countNonZero(cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)[1]) / (w * h)
        edge_density = float(np.sum(cv2.Canny(gray, 50, 150) > 0)) / (w * h)
        
        vehicle_type = self._classify_from_features(aspect, area_ratio, edge_density, w * h)
        
        result = {
            "vehicle_type": vehicle_type["type"],
            "confidence": round(vehicle_type["confidence"], 3),
            "features": {
                "aspect_ratio": round(aspect, 2),
                "area_ratio": round(area_ratio, 3),
                "edge_density": round(edge_density, 4)
            },
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.vehicle_history.append(result)
        return result

    def _classify_from_features(self, aspect, area_ratio, edge_density, size) -> dict:
        if aspect > 2.5: return {"type": "bus", "confidence": 0.6}
        if aspect > 1.8 and area_ratio > 0.6: return {"type": "truck", "confidence": 0.55}
        if area_ratio > 0.55 and aspect > 1.3: return {"type": "suv", "confidence": 0.55}
        if aspect < 0.8: return {"type": "motorcycle", "confidence": 0.5}
        if edge_density < 0.15 and aspect > 1.2: return {"type": "van", "confidence": 0.5}
        if edge_density > 0.25: return {"type": "sedan", "confidence": 0.5}
        return {"type": "sedan", "confidence": 0.45}


# Singleton instances
privacy_service = PrivacyMaskService()
enhancement_service = ImageEnhancementService()
ensemble_service = ModelEnsembleService()
notification_template_service = NotificationTemplateService()
license_plate_service = LicensePlateService()
person_reid_service = PersonReIdService()
activity_service = ActivityRecognitionService()
package_service = PackageDetectionService()
abandoned_object_service = AbandonedObjectService()
vehicle_service = VehicleClassificationService()
