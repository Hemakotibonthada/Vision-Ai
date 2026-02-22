"""
Jarvis AI - Face Recognition Service
=====================================
Handles owner recognition, face enrollment, and intruder detection.
Uses face_recognition library (dlib-based) for robust face matching.
"""
import os
import json
import time
import pickle
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from loguru import logger

try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False
    logger.warning("face_recognition not installed. Using OpenCV fallback.")

from jarvis.config import settings


class FaceIdentity:
    """Represents a known person's face data."""

    def __init__(self, name: str, role: str = "unknown"):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.role = role  # owner, family, friend, known, unknown
        self.encodings: List[np.ndarray] = []
        self.photos: List[str] = []
        self.first_seen = datetime.now().isoformat()
        self.last_seen = datetime.now().isoformat()
        self.seen_count = 0
        self.avg_encoding: Optional[np.ndarray] = None

    def add_encoding(self, encoding: np.ndarray, photo_path: str = None):
        self.encodings.append(encoding)
        if photo_path:
            self.photos.append(photo_path)
        self.seen_count += 1
        self.last_seen = datetime.now().isoformat()
        # Update average encoding for better matching
        if len(self.encodings) > 1:
            self.avg_encoding = np.mean(self.encodings, axis=0)
        else:
            self.avg_encoding = encoding

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "seen_count": self.seen_count,
            "num_encodings": len(self.encodings),
            "photos": self.photos[-5:]  # Last 5 photos
        }


class FaceRecognitionService:
    """Manages face detection, recognition, and enrollment."""

    def __init__(self):
        self.known_faces: Dict[str, FaceIdentity] = {}
        self.owner_id: Optional[str] = None
        self.face_cascade = None
        self._load_cascade()
        self._load_face_db()
        logger.info(f"Face recognition service initialized. Known faces: {len(self.known_faces)}")

    def _load_cascade(self):
        """Load OpenCV Haar cascade as fallback."""
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def _load_face_db(self):
        """Load saved face database from disk."""
        db_path = os.path.join(settings.FACE_DB_DIR, "face_db.pkl")
        meta_path = os.path.join(settings.FACE_DB_DIR, "face_meta.json")

        if os.path.exists(db_path):
            try:
                with open(db_path, "rb") as f:
                    data = pickle.load(f)
                    self.known_faces = data.get("faces", {})
                    self.owner_id = data.get("owner_id")
                logger.info(f"Loaded {len(self.known_faces)} faces from database")
            except Exception as e:
                logger.error(f"Failed to load face DB: {e}")

    def _save_face_db(self):
        """Persist face database to disk."""
        db_path = os.path.join(settings.FACE_DB_DIR, "face_db.pkl")
        meta_path = os.path.join(settings.FACE_DB_DIR, "face_meta.json")

        try:
            with open(db_path, "wb") as f:
                pickle.dump({
                    "faces": self.known_faces,
                    "owner_id": self.owner_id
                }, f)

            # Save readable metadata
            meta = {
                "owner_id": self.owner_id,
                "total_faces": len(self.known_faces),
                "faces": {k: v.to_dict() for k, v in self.known_faces.items()},
                "updated_at": datetime.now().isoformat()
            }
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)

            logger.debug("Face database saved")
        except Exception as e:
            logger.error(f"Failed to save face DB: {e}")

    # ================================================================
    # Face Detection
    # ================================================================
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect face locations in a frame. Returns list of (top, right, bottom, left)."""
        if FACE_REC_AVAILABLE:
            # Downscale for speed
            small = cv2.resize(frame, (0, 0),
                             fx=settings.FACE_DETECTION_SCALE,
                             fy=settings.FACE_DETECTION_SCALE)
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            locations = face_recognition.face_locations(
                rgb_small, model=settings.FACE_RECOGNITION_MODEL
            )

            # Scale back up
            scale = 1.0 / settings.FACE_DETECTION_SCALE
            return [(int(t * scale), int(r * scale),
                     int(b * scale), int(l * scale))
                    for (t, r, b, l) in locations]
        else:
            # OpenCV fallback
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detections = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            return [(y, x + w, y + h, x) for (x, y, w, h) in detections]

    def get_face_encodings(self, frame: np.ndarray,
                           locations: List[Tuple] = None) -> List[np.ndarray]:
        """Get 128-dim face encodings."""
        if not FACE_REC_AVAILABLE:
            return []

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if locations:
            return face_recognition.face_encodings(rgb, locations)
        return face_recognition.face_encodings(rgb)

    # ================================================================
    # Face Recognition
    # ================================================================
    def recognize_faces(self, frame: np.ndarray) -> List[Dict]:
        """Detect and identify faces in a frame.
        
        Returns list of:
        {
            "identity": FaceIdentity or None,
            "location": (top, right, bottom, left),
            "is_owner": bool,
            "is_known": bool,
            "confidence": float,
            "name": str
        }
        """
        locations = self.detect_faces(frame)
        if not locations:
            return []

        encodings = self.get_face_encodings(frame, locations)
        results = []

        for location, encoding in zip(locations, encodings):
            match = self._find_match(encoding)

            if match:
                identity, distance = match
                identity.last_seen = datetime.now().isoformat()
                identity.seen_count += 1

                results.append({
                    "identity": identity,
                    "location": location,
                    "is_owner": identity.id == self.owner_id,
                    "is_known": True,
                    "confidence": round(1.0 - distance, 3),
                    "name": identity.name,
                    "role": identity.role
                })
            else:
                results.append({
                    "identity": None,
                    "location": location,
                    "is_owner": False,
                    "is_known": False,
                    "confidence": 0.0,
                    "name": "Unknown",
                    "role": "unknown"
                })

        return results

    def _find_match(self, encoding: np.ndarray) -> Optional[Tuple[FaceIdentity, float]]:
        """Find the best matching known face for an encoding."""
        if not FACE_REC_AVAILABLE or not self.known_faces:
            return None

        best_match = None
        best_distance = settings.FACE_ENCODING_TOLERANCE

        for identity in self.known_faces.values():
            if identity.avg_encoding is not None:
                # Compare against average encoding (more stable)
                distance = face_recognition.face_distance(
                    [identity.avg_encoding], encoding
                )[0]
            elif identity.encodings:
                # Compare against all encodings
                distances = face_recognition.face_distance(
                    identity.encodings, encoding
                )
                distance = min(distances)
            else:
                continue

            if distance < best_distance:
                best_distance = distance
                best_match = (identity, distance)

        return best_match

    # ================================================================
    # Owner Enrollment
    # ================================================================
    def register_owner(self, frame: np.ndarray, name: str = None) -> Dict:
        """Register the owner's face from a frame."""
        name = name or settings.OWNER_NAME
        locations = self.detect_faces(frame)

        if not locations:
            return {"success": False, "error": "No face detected"}
        if len(locations) > 1:
            return {"success": False, "error": "Multiple faces detected. Please be alone."}

        encodings = self.get_face_encodings(frame, locations)
        if not encodings:
            return {"success": False, "error": "Could not encode face"}

        # Save photo
        photo_path = os.path.join(
            settings.FACE_DB_DIR, f"owner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        )
        t, r, b, l = locations[0]
        face_img = frame[max(0, t-20):b+20, max(0, l-20):r+20]
        cv2.imwrite(photo_path, face_img)

        # Create or update owner identity
        if self.owner_id and self.owner_id in self.known_faces:
            identity = self.known_faces[self.owner_id]
            identity.add_encoding(encodings[0], photo_path)
        else:
            identity = FaceIdentity(name=name, role="owner")
            identity.add_encoding(encodings[0], photo_path)
            self.known_faces[identity.id] = identity
            self.owner_id = identity.id

        self._save_face_db()

        return {
            "success": True,
            "owner_id": self.owner_id,
            "name": name,
            "total_samples": len(identity.encodings),
            "needed": max(0, settings.FACE_REGISTRATION_SAMPLES - len(identity.encodings)),
            "photo": photo_path
        }

    def register_known_person(self, frame: np.ndarray, name: str,
                               role: str = "known") -> Dict:
        """Register a known person (family, friend, etc.)."""
        locations = self.detect_faces(frame)
        if not locations:
            return {"success": False, "error": "No face detected"}

        encodings = self.get_face_encodings(frame, locations)
        if not encodings:
            return {"success": False, "error": "Could not encode face"}

        # Check if already known
        match = self._find_match(encodings[0])
        if match:
            identity, _ = match
            identity.add_encoding(encodings[0])
            identity.name = name
            identity.role = role
        else:
            identity = FaceIdentity(name=name, role=role)
            identity.add_encoding(encodings[0])
            self.known_faces[identity.id] = identity

        self._save_face_db()

        return {
            "success": True,
            "person_id": identity.id,
            "name": name,
            "role": role,
            "total_samples": len(identity.encodings)
        }

    # ================================================================
    # Intruder Handling
    # ================================================================
    def capture_intruder(self, frame: np.ndarray,
                         location: Tuple[int, int, int, int]) -> Dict:
        """Capture and save an intruder's photo."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"intruder_{timestamp}.jpg"
        filepath = os.path.join(settings.INTRUDER_DIR, filename)

        # Save full frame
        cv2.imwrite(filepath, frame)

        # Save cropped face
        t, r, b, l = location
        face_img = frame[max(0, t-30):b+30, max(0, l-30):r+30]
        face_path = os.path.join(settings.INTRUDER_DIR, f"face_{filename}")
        cv2.imwrite(face_path, face_img)

        # Get encoding for future matching
        encodings = self.get_face_encodings(frame, [location])

        # Auto-register as unknown person
        if encodings:
            match = self._find_match(encodings[0])
            if match:
                identity, _ = match
                identity.add_encoding(encodings[0], filepath)
            else:
                identity = FaceIdentity(name=f"Unknown_{timestamp[:8]}", role="unknown")
                identity.add_encoding(encodings[0], filepath)
                self.known_faces[identity.id] = identity
            self._save_face_db()

        # Cleanup old intruder photos
        self._cleanup_intruder_photos()

        return {
            "timestamp": timestamp,
            "full_image": filepath,
            "face_image": face_path,
            "location": location
        }

    def _cleanup_intruder_photos(self):
        """Keep only the most recent intruder photos."""
        files = sorted(Path(settings.INTRUDER_DIR).glob("intruder_*.jpg"))
        if len(files) > settings.MAX_INTRUDER_PHOTOS:
            for f in files[:-settings.MAX_INTRUDER_PHOTOS]:
                f.unlink(missing_ok=True)

    # ================================================================
    # Utilities
    # ================================================================
    def draw_faces(self, frame: np.ndarray, results: List[Dict]) -> np.ndarray:
        """Draw face bounding boxes and labels on frame."""
        annotated = frame.copy()

        for r in results:
            t, right, b, l = r["location"]

            if r["is_owner"]:
                color = (0, 255, 0)  # Green for owner
                label = f"{r['name']} (Owner)"
            elif r["is_known"]:
                color = (255, 165, 0)  # Orange for known
                label = f"{r['name']} ({r['role']})"
            else:
                color = (0, 0, 255)  # Red for unknown
                label = f"UNKNOWN ({r['confidence']:.0%})"

            cv2.rectangle(annotated, (l, t), (right, b), color, 2)
            cv2.putText(annotated, label, (l, t - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        return annotated

    def get_owner_info(self) -> Optional[Dict]:
        """Get owner identity info."""
        if self.owner_id and self.owner_id in self.known_faces:
            return self.known_faces[self.owner_id].to_dict()
        return None

    def get_all_faces(self) -> List[Dict]:
        """Get all known faces."""
        return [f.to_dict() for f in self.known_faces.values()]

    def is_owner_registered(self) -> bool:
        """Check if the owner's face is registered."""
        return (self.owner_id is not None and
                self.owner_id in self.known_faces and
                len(self.known_faces[self.owner_id].encodings) > 0)


# Singleton
face_service = FaceRecognitionService()
