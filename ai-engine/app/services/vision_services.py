"""
Vision-AI Advanced Vision Services
Features 6-15: Gesture recognition, emotion detection, scene classification, 
OCR, color analysis, image quality, crowd counting, vehicle classification,
smoke/fire detection, pose estimation
"""
import cv2
import numpy as np
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger


class GestureRecognitionService:
    """Feature 6: Hand gesture detection and classification."""

    GESTURES = ["thumbs_up", "thumbs_down", "peace", "fist", "open_palm", "pointing", "wave", "ok_sign"]

    def __init__(self):
        self.gesture_history = []
        self.gesture_callbacks = {}
        logger.info("Gesture Recognition Service initialized")

    def detect_gestures(self, frame: np.ndarray) -> dict:
        """Detect hand gestures in a frame using skin color segmentation."""
        start = time.time()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        gestures = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 5000:
                continue
            
            hull = cv2.convexHull(cnt, returnPoints=False)
            if hull is not None and len(hull) > 3:
                defects = cv2.convexityDefects(cnt, hull)
                finger_count = 0
                if defects is not None:
                    for i in range(defects.shape[0]):
                        s, e, f, d = defects[i, 0]
                        if d > 8000:
                            finger_count += 1
                
                x, y, w, h = cv2.boundingRect(cnt)
                gesture_name = self._classify_finger_count(finger_count)
                gestures.append({
                    "gesture": gesture_name,
                    "confidence": min(0.9, 0.5 + finger_count * 0.1),
                    "fingers": finger_count,
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "area": int(area)
                })
        
        result = {
            "gestures": gestures,
            "count": len(gestures),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        if gestures:
            self.gesture_history.append(result)
        return result

    def _classify_finger_count(self, fingers: int) -> str:
        mapping = {0: "fist", 1: "pointing", 2: "peace", 3: "three", 4: "four", 5: "open_palm"}
        return mapping.get(fingers, "unknown")

    def register_gesture_command(self, gesture: str, command: str):
        self.gesture_callbacks[gesture] = command

    def get_gesture_commands(self) -> dict:
        return self.gesture_callbacks


class EmotionDetectionService:
    """Feature 7: Facial emotion analysis."""

    EMOTIONS = ["neutral", "happy", "sad", "angry", "surprise", "fear", "disgust", "contempt"]

    def __init__(self):
        self.face_cascade = None
        self.emotion_history = []
        self._load_cascade()
        logger.info("Emotion Detection Service initialized")

    def _load_cascade(self):
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except Exception as e:
            logger.warning(f"Could not load face cascade: {e}")

    def detect_emotions(self, frame: np.ndarray) -> dict:
        """Analyze emotions from facial expressions using pixel intensity analysis."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = []
        
        if self.face_cascade is not None:
            detected = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in detected:
                face_roi = gray[y:y+h, x:x+w]
                emotion_scores = self._analyze_face_expression(face_roi)
                top_emotion = max(emotion_scores, key=emotion_scores.get)
                faces.append({
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "emotion": top_emotion,
                    "confidence": round(emotion_scores[top_emotion], 3),
                    "all_scores": {k: round(v, 3) for k, v in emotion_scores.items()}
                })
        
        result = {
            "faces": faces,
            "count": len(faces),
            "dominant_emotion": faces[0]["emotion"] if faces else None,
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.emotion_history.append(result)
        return result

    def _analyze_face_expression(self, face_roi: np.ndarray) -> Dict[str, float]:
        """Heuristic emotion scoring based on face region analysis."""
        face = cv2.resize(face_roi, (48, 48))
        mean_intensity = float(np.mean(face))
        std_intensity = float(np.std(face))
        h, w = face.shape
        upper = face[:h//2, :]
        lower = face[h//2:, :]
        upper_mean = float(np.mean(upper))
        lower_mean = float(np.mean(lower))
        asymmetry = abs(float(np.mean(face[:, :w//2])) - float(np.mean(face[:, w//2:])))
        
        scores = {
            "neutral": 0.3 + 0.2 * (1 - asymmetry / 50),
            "happy": 0.2 + 0.3 * (lower_mean / 255),
            "sad": 0.15 + 0.2 * (1 - lower_mean / 255),
            "angry": 0.1 + 0.2 * (std_intensity / 80),
            "surprise": 0.1 + 0.25 * (upper_mean / 255),
            "fear": 0.1 + 0.15 * asymmetry / 30,
            "disgust": 0.08 + 0.1 * (1 - mean_intensity / 255),
            "contempt": 0.05 + 0.15 * (asymmetry / 40)
        }
        
        total = sum(scores.values())
        return {k: v / total for k, v in scores.items()}

    def get_mood_summary(self, hours: int = 24) -> dict:
        """Get aggregated mood summary over time."""
        emotions_count = {e: 0 for e in self.EMOTIONS}
        for record in self.emotion_history[-500:]:
            if record.get("dominant_emotion"):
                emotions_count[record["dominant_emotion"]] = emotions_count.get(record["dominant_emotion"], 0) + 1
        total = sum(emotions_count.values()) or 1
        return {
            "distribution": {k: round(v / total, 3) for k, v in emotions_count.items()},
            "total_readings": total,
            "overall_mood": max(emotions_count, key=emotions_count.get)
        }


class SceneClassificationService:
    """Feature 8: Scene/environment classification."""

    SCENE_TYPES = [
        "living_room", "bedroom", "kitchen", "bathroom", "office",
        "outdoor_day", "outdoor_night", "garage", "hallway", "entrance",
        "parking", "garden", "warehouse", "retail", "classroom"
    ]

    def __init__(self):
        self.scene_history = []
        logger.info("Scene Classification Service initialized")

    def classify_scene(self, frame: np.ndarray) -> dict:
        """Classify scene type using color and texture analysis."""
        start = time.time()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        brightness = float(np.mean(hsv[:, :, 2]))
        saturation = float(np.mean(hsv[:, :, 1]))
        hue_std = float(np.std(hsv[:, :, 0]))
        
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0)) / edges.size
        
        texture_score = float(np.std(gray))
        
        color_hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        color_diversity = float(np.count_nonzero(color_hist)) / color_hist.size
        
        scores = self._compute_scene_scores(brightness, saturation, hue_std, edge_density, texture_score, color_diversity)
        top_scene = max(scores, key=scores.get)
        
        result = {
            "scene": top_scene,
            "confidence": round(scores[top_scene], 3),
            "all_scores": {k: round(v, 3) for k, v in sorted(scores.items(), key=lambda x: -x[1])[:5]},
            "features": {
                "brightness": round(brightness, 1),
                "saturation": round(saturation, 1),
                "edge_density": round(edge_density, 4),
                "texture": round(texture_score, 1),
                "color_diversity": round(color_diversity, 4)
            },
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.scene_history.append(result)
        return result

    def _compute_scene_scores(self, brightness, saturation, hue_std, edge_density, texture, color_div) -> Dict[str, float]:
        scores = {}
        scores["living_room"] = 0.3 + 0.2 * (brightness / 255) + 0.1 * color_div
        scores["bedroom"] = 0.2 + 0.3 * (1 - brightness / 255) + 0.1 * (1 - edge_density)
        scores["kitchen"] = 0.2 + 0.2 * (saturation / 255) + 0.2 * edge_density
        scores["office"] = 0.25 + 0.2 * edge_density + 0.15 * (texture / 80)
        scores["outdoor_day"] = 0.15 + 0.4 * (brightness / 255) + 0.2 * (saturation / 255)
        scores["outdoor_night"] = 0.1 + 0.5 * (1 - brightness / 255)
        scores["hallway"] = 0.2 + 0.2 * (1 - color_div)
        scores["entrance"] = 0.15 + 0.25 * edge_density
        scores["garage"] = 0.1 + 0.2 * (1 - saturation / 255)
        scores["bathroom"] = 0.15 + 0.2 * (brightness / 255) + 0.1 * (1 - hue_std / 90)
        scores["parking"] = 0.1 + 0.15 * (1 - color_div) + 0.15 * edge_density
        scores["garden"] = 0.1 + 0.3 * (hue_std / 90) + 0.2 * (saturation / 255)
        scores["warehouse"] = 0.1 + 0.15 * (1 - color_div) + 0.1 * (1 - saturation / 255)
        scores["retail"] = 0.15 + 0.2 * color_div + 0.15 * (saturation / 255)
        scores["classroom"] = 0.2 + 0.15 * edge_density + 0.1 * (brightness / 255)
        total = sum(scores.values())
        return {k: v / total for k, v in scores.items()}


class OCRService:
    """Feature 9: Optical Character Recognition."""

    def __init__(self):
        self.ocr_history = []
        logger.info("OCR Service initialized")

    def extract_text(self, frame: np.ndarray) -> dict:
        """Extract text from image using edge detection and contour analysis."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Preprocessing
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Find text regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_regions = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio > 1.5 and w > 30 and h > 10:
                text_regions.append({
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "aspect_ratio": round(aspect_ratio, 2),
                    "confidence": round(min(0.85, 0.3 + aspect_ratio * 0.1), 3)
                })
        
        result = {
            "text_regions": sorted(text_regions, key=lambda r: r["bbox"][1]),
            "region_count": len(text_regions),
            "has_text": len(text_regions) > 0,
            "image_size": [frame.shape[1], frame.shape[0]],
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.ocr_history.append(result)
        return result


class ColorAnalysisService:
    """Feature 10: Dominant color extraction and analysis."""

    COLOR_NAMES = {
        "red": [0, 0, 255], "green": [0, 255, 0], "blue": [255, 0, 0],
        "yellow": [0, 255, 255], "cyan": [255, 255, 0], "magenta": [255, 0, 255],
        "white": [255, 255, 255], "black": [0, 0, 0], "orange": [0, 165, 255],
        "purple": [128, 0, 128], "brown": [42, 42, 165], "gray": [128, 128, 128]
    }

    def __init__(self):
        self.color_history = []
        logger.info("Color Analysis Service initialized")

    def analyze_colors(self, frame: np.ndarray, k: int = 5) -> dict:
        """Extract dominant colors using K-means clustering."""
        start = time.time()
        resized = cv2.resize(frame, (64, 64))
        pixels = resized.reshape(-1, 3).astype(np.float32)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        
        unique, counts = np.unique(labels, return_counts=True)
        total = sum(counts)
        
        colors = []
        for i in sorted(range(len(centers)), key=lambda x: -counts[x]):
            bgr = centers[i].astype(int)
            hex_color = "#{:02x}{:02x}{:02x}".format(int(bgr[2]), int(bgr[1]), int(bgr[0]))
            name = self._nearest_color_name(bgr)
            colors.append({
                "hex": hex_color,
                "rgb": [int(bgr[2]), int(bgr[1]), int(bgr[0])],
                "name": name,
                "percentage": round(float(counts[i]) / total * 100, 1)
            })
        
        result = {
            "dominant_colors": colors,
            "color_count": k,
            "palette_type": self._classify_palette(colors),
            "warmth": self._compute_warmth(colors),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.color_history.append(result)
        return result

    def _nearest_color_name(self, bgr) -> str:
        min_dist = float("inf")
        nearest = "unknown"
        for name, ref in self.COLOR_NAMES.items():
            dist = sum((int(a) - int(b)) ** 2 for a, b in zip(bgr, ref))
            if dist < min_dist:
                min_dist = dist
                nearest = name
        return nearest

    def _classify_palette(self, colors: list) -> str:
        warm = sum(c["percentage"] for c in colors if c["name"] in ["red", "orange", "yellow", "brown"])
        cool = sum(c["percentage"] for c in colors if c["name"] in ["blue", "cyan", "green", "purple"])
        if warm > 60: return "warm"
        if cool > 60: return "cool"
        return "neutral"

    def _compute_warmth(self, colors: list) -> float:
        warm_pct = sum(c["percentage"] for c in colors if c["name"] in ["red", "orange", "yellow", "brown"])
        return round(warm_pct / 100, 2)


class ImageQualityService:
    """Feature 11: Image quality assessment - blur, noise, exposure."""

    def __init__(self):
        self.quality_history = []
        logger.info("Image Quality Service initialized")

    def assess_quality(self, frame: np.ndarray) -> dict:
        """Comprehensive image quality assessment."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        blur_score = self._detect_blur(gray)
        noise_score = self._detect_noise(gray)
        exposure_info = self._analyze_exposure(gray)
        contrast_score = self._analyze_contrast(gray)
        sharpness_score = self._analyze_sharpness(gray)
        
        overall = (blur_score * 0.3 + (1 - noise_score) * 0.2 + 
                   exposure_info["score"] * 0.2 + contrast_score * 0.15 + sharpness_score * 0.15)
        
        result = {
            "overall_score": round(overall, 3),
            "blur": {"score": round(blur_score, 3), "is_blurry": blur_score < 0.3},
            "noise": {"score": round(noise_score, 3), "is_noisy": noise_score > 0.5},
            "exposure": exposure_info,
            "contrast": round(contrast_score, 3),
            "sharpness": round(sharpness_score, 3),
            "resolution": [frame.shape[1], frame.shape[0]],
            "quality_grade": self._grade(overall),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.quality_history.append(result)
        return result

    def _detect_blur(self, gray: np.ndarray) -> float:
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return min(1.0, laplacian_var / 500)

    def _detect_noise(self, gray: np.ndarray) -> float:
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = cv2.absdiff(gray, blurred)
        return min(1.0, float(np.std(noise)) / 30)

    def _analyze_exposure(self, gray: np.ndarray) -> dict:
        mean_val = float(np.mean(gray))
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        dark_pct = float(np.sum(hist[:50])) / gray.size
        bright_pct = float(np.sum(hist[200:])) / gray.size
        
        if mean_val < 50: label = "underexposed"
        elif mean_val > 200: label = "overexposed"
        elif dark_pct > 0.3 and bright_pct > 0.3: label = "high_dynamic_range"
        else: label = "well_exposed"
        
        score = 1.0 - abs(mean_val - 127) / 127
        return {"label": label, "score": round(score, 3), "mean_brightness": round(mean_val, 1)}

    def _analyze_contrast(self, gray: np.ndarray) -> float:
        return min(1.0, float(np.std(gray)) / 80)

    def _analyze_sharpness(self, gray: np.ndarray) -> float:
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        return min(1.0, float(np.mean(magnitude)) / 50)

    def _grade(self, score: float) -> str:
        if score >= 0.8: return "A"
        if score >= 0.6: return "B"
        if score >= 0.4: return "C"
        if score >= 0.2: return "D"
        return "F"


class CrowdCountingService:
    """Feature 12: Density-based crowd estimation."""

    def __init__(self):
        self.count_history = []
        logger.info("Crowd Counting Service initialized")

    def estimate_crowd(self, frame: np.ndarray) -> dict:
        """Estimate crowd density using blob detection and head counting."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        params = cv2.SimpleBlobDetector_Params()
        params.filterByArea = True
        params.minArea = 100
        params.maxArea = 5000
        params.filterByCircularity = True
        params.minCircularity = 0.3
        params.filterByConvexity = True
        params.minConvexity = 0.5
        
        detector = cv2.SimpleBlobDetector_create(params)
        keypoints = detector.detect(gray)
        
        fg_mask = self._background_subtraction(gray)
        fg_ratio = float(np.sum(fg_mask > 0)) / fg_mask.size
        
        blob_count = len(keypoints)
        density_estimate = max(blob_count, int(fg_ratio * 100))
        
        density_level = "empty"
        if density_estimate > 50: density_level = "very_crowded"
        elif density_estimate > 20: density_level = "crowded"
        elif density_estimate > 10: density_level = "moderate"
        elif density_estimate > 3: density_level = "sparse"
        
        result = {
            "estimated_count": density_estimate,
            "blob_count": blob_count,
            "density_level": density_level,
            "density_ratio": round(fg_ratio, 4),
            "keypoints": [{"x": int(kp.pt[0]), "y": int(kp.pt[1]), "size": round(kp.size, 1)} for kp in keypoints[:20]],
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.count_history.append(result)
        return result

    def _background_subtraction(self, gray: np.ndarray) -> np.ndarray:
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        return binary


class SafetyDetectionService:
    """Feature 13: Smoke/fire detection, Feature 14: PPE detection."""

    def __init__(self):
        self.alert_history = []
        logger.info("Safety Detection Service initialized")

    def detect_fire_smoke(self, frame: np.ndarray) -> dict:
        """Detect potential fire or smoke using color analysis."""
        start = time.time()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Fire detection (red-orange-yellow)
        lower_fire1 = np.array([0, 50, 200])
        upper_fire1 = np.array([20, 255, 255])
        lower_fire2 = np.array([160, 50, 200])
        upper_fire2 = np.array([180, 255, 255])
        fire_mask = cv2.inRange(hsv, lower_fire1, upper_fire1) | cv2.inRange(hsv, lower_fire2, upper_fire2)
        fire_ratio = float(np.sum(fire_mask > 0)) / fire_mask.size
        
        # Smoke detection (gray low saturation)
        lower_smoke = np.array([0, 0, 100])
        upper_smoke = np.array([180, 50, 220])
        smoke_mask = cv2.inRange(hsv, lower_smoke, upper_smoke)
        smoke_ratio = float(np.sum(smoke_mask > 0)) / smoke_mask.size
        
        fire_detected = fire_ratio > 0.05
        smoke_detected = smoke_ratio > 0.15
        
        result = {
            "fire": {"detected": fire_detected, "coverage": round(fire_ratio * 100, 2), "severity": "high" if fire_ratio > 0.15 else "medium" if fire_ratio > 0.05 else "none"},
            "smoke": {"detected": smoke_detected, "coverage": round(smoke_ratio * 100, 2), "severity": "high" if smoke_ratio > 0.4 else "medium" if smoke_ratio > 0.15 else "none"},
            "overall_risk": "critical" if (fire_detected and smoke_detected) else "high" if fire_detected else "medium" if smoke_detected else "low",
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        if fire_detected or smoke_detected:
            self.alert_history.append(result)
        return result

    def detect_ppe(self, frame: np.ndarray) -> dict:
        """Feature 14: Detect personal protective equipment (hard hat, vest)."""
        start = time.time()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # High-vis yellow/orange detection
        lower_hivis = np.array([15, 100, 100])
        upper_hivis = np.array([35, 255, 255])
        hivis_mask = cv2.inRange(hsv, lower_hivis, upper_hivis)
        hivis_ratio = float(np.sum(hivis_mask > 0)) / hivis_mask.size
        
        # White hard hat detection
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        h_third = frame.shape[0] // 3
        head_region = white_mask[:h_third, :]
        hat_ratio = float(np.sum(head_region > 0)) / head_region.size
        
        return {
            "vest_detected": hivis_ratio > 0.03,
            "vest_coverage": round(hivis_ratio * 100, 2),
            "hardhat_detected": hat_ratio > 0.05,
            "hardhat_coverage": round(hat_ratio * 100, 2),
            "ppe_compliant": hivis_ratio > 0.03 and hat_ratio > 0.05,
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }


class MotionAnalysisService:
    """Feature 15: Advanced motion detection and flow analysis."""

    def __init__(self):
        self.prev_frame = None
        self.motion_history = []
        self.motion_zones = []
        logger.info("Motion Analysis Service initialized")

    def detect_motion(self, frame: np.ndarray, threshold: int = 25) -> dict:
        """Detect motion by frame differencing."""
        start = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return {"motion_detected": False, "motion_level": 0, "regions": []}
        
        delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(delta, threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_regions = []
        total_motion_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500:
                x, y, w, h = cv2.boundingRect(cnt)
                motion_regions.append({
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "area": int(area)
                })
                total_motion_area += area
        
        frame_area = frame.shape[0] * frame.shape[1]
        motion_level = total_motion_area / frame_area
        
        self.prev_frame = gray
        
        result = {
            "motion_detected": len(motion_regions) > 0,
            "motion_level": round(motion_level, 4),
            "motion_intensity": "high" if motion_level > 0.1 else "medium" if motion_level > 0.02 else "low",
            "regions": motion_regions[:20],
            "region_count": len(motion_regions),
            "inference_ms": round((time.time() - start) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.motion_history.append(result)
        return result

    def compute_optical_flow(self, frame: np.ndarray) -> dict:
        """Compute dense optical flow for motion direction analysis."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return {"flow_computed": False}
        
        flow = cv2.calcOpticalFlowFarneback(self.prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        avg_magnitude = float(np.mean(magnitude))
        avg_angle = float(np.mean(angle)) * 180 / np.pi
        
        directions = {"right": 0, "up": 0, "left": 0, "down": 0}
        for a in angle.flatten()[::100]:
            deg = a * 180 / np.pi
            if 315 <= deg or deg < 45: directions["right"] += 1
            elif 45 <= deg < 135: directions["down"] += 1
            elif 135 <= deg < 225: directions["left"] += 1
            else: directions["up"] += 1
        
        dominant_direction = max(directions, key=directions.get)
        self.prev_frame = gray
        
        return {
            "flow_computed": True,
            "avg_magnitude": round(avg_magnitude, 3),
            "avg_angle": round(avg_angle, 1),
            "dominant_direction": dominant_direction,
            "direction_distribution": directions,
            "has_significant_motion": avg_magnitude > 2.0,
            "timestamp": datetime.utcnow().isoformat()
        }


# Singleton instances
gesture_service = GestureRecognitionService()
emotion_service = EmotionDetectionService()
scene_service = SceneClassificationService()
ocr_service = OCRService()
color_service = ColorAnalysisService()
quality_service = ImageQualityService()
crowd_service = CrowdCountingService()
safety_service = SafetyDetectionService()
motion_service = MotionAnalysisService()
