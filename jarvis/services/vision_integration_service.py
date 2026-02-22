"""
Jarvis AI - Vision AI Integration Service
=============================================
Bridges Jarvis to the main Vision-AI engine (FastAPI on port 8000).
Provides object detection, classification, tracking via the existing AI.
"""
import asyncio
import json
from typing import Dict, Optional, List
from datetime import datetime
from io import BytesIO

import httpx
import cv2
import numpy as np
from loguru import logger

from jarvis.config import settings


class VisionAIService:
    """Client for the Vision-AI engine API."""

    def __init__(self):
        self.base_url = settings.VISION_API_URL
        self._available = False
        self._last_check = 0
        self._models_loaded: List[str] = []
        logger.info(f"Vision AI integration initialized. API: {self.base_url}")

    async def check_health(self) -> bool:
        """Check if Vision-AI engine is online."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/health")
                self._available = resp.status_code == 200
                return self._available
        except Exception:
            self._available = False
            return False

    async def detect_objects(self, frame: np.ndarray, confidence: float = 0.5) -> Dict:
        """Send a frame to Vision-AI for object detection."""
        try:
            _, buffer = cv2.imencode(".jpg", frame)
            img_bytes = buffer.tobytes()

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/detect",
                    files={"file": ("frame.jpg", img_bytes, "image/jpeg")},
                    data={"confidence": str(confidence)},
                )
                if resp.status_code == 200:
                    return resp.json()
                else:
                    logger.error(f"Detection failed: {resp.status_code}")
                    return {"error": resp.text}
        except Exception as e:
            logger.error(f"Vision AI detect_objects failed: {e}")
            return {"error": str(e)}

    async def classify_image(self, frame: np.ndarray) -> Dict:
        """Classify an image using the Vision-AI engine."""
        try:
            _, buffer = cv2.imencode(".jpg", frame)
            img_bytes = buffer.tobytes()

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/classify",
                    files={"file": ("frame.jpg", img_bytes, "image/jpeg")},
                )
                return resp.json() if resp.status_code == 200 else {"error": resp.text}
        except Exception as e:
            logger.error(f"Vision AI classify failed: {e}")
            return {"error": str(e)}

    async def track_objects(self, frame: np.ndarray) -> Dict:
        """Track objects using the Vision-AI engine."""
        try:
            _, buffer = cv2.imencode(".jpg", frame)
            img_bytes = buffer.tobytes()

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/track",
                    files={"file": ("frame.jpg", img_bytes, "image/jpeg")},
                )
                return resp.json() if resp.status_code == 200 else {"error": resp.text}
        except Exception as e:
            logger.error(f"Vision AI track failed: {e}")
            return {"error": str(e)}

    async def count_objects(self, frame: np.ndarray, target_class: str = "person") -> int:
        """Count specific objects in frame."""
        result = await self.detect_objects(frame)
        if "error" in result:
            return 0

        detections = result.get("detections", [])
        return sum(1 for d in detections if d.get("class", "").lower() == target_class.lower())

    async def get_models(self) -> List[Dict]:
        """List available AI models."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    self._models_loaded = [m.get("name", "") for m in data.get("models", [])]
                    return data.get("models", [])
                return []
        except Exception as e:
            logger.error(f"Get models failed: {e}")
            return []

    async def get_detections_summary(self, frame: np.ndarray) -> str:
        """Get a human-readable summary of what's in the frame."""
        result = await self.detect_objects(frame)
        if "error" in result:
            return "Unable to analyze the scene right now."

        detections = result.get("detections", [])
        if not detections:
            return "No objects detected in the current view."

        # Group by class
        counts: Dict[str, int] = {}
        for d in detections:
            cls = d.get("class", "unknown")
            counts[cls] = counts.get(cls, 0) + 1

        parts = [f"{count} {cls}{'s' if count > 1 else ''}" for cls, count in counts.items()]
        return f"I can see: {', '.join(parts)}."

    async def analyze_scene(self, frame: np.ndarray) -> Dict:
        """Full scene analysis — detection + classification."""
        detection = await self.detect_objects(frame)
        classification = await self.classify_image(frame)
        return {
            "detections": detection.get("detections", []),
            "classification": classification,
            "timestamp": datetime.now().isoformat(),
        }

    @property
    def is_available(self) -> bool:
        return self._available


# Singleton
vision_service = VisionAIService()
