"""
Jarvis AI - Room Presence & Security Service
==============================================
Monitors room occupancy using camera + face recognition.
Manages intruder detection, recording, and security alerts.
"""
import asyncio
import time
import os
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass, field

import cv2
import numpy as np
from loguru import logger

from jarvis.config import settings
from jarvis.services.face_recognition_service import face_service
from jarvis.services.camera_service import camera_service


class PresenceState(str, Enum):
    EMPTY = "empty"
    OWNER_PRESENT = "owner_present"
    UNKNOWN_PERSON = "unknown_person"
    MULTIPLE_PEOPLE = "multiple_people"


@dataclass
class IntruderRecord:
    timestamp: str
    photo_path: str
    video_path: Optional[str] = None
    duration_seconds: float = 0.0
    face_encoding: Optional[list] = None
    activity_summary: str = ""


@dataclass
class RoomState:
    presence: PresenceState = PresenceState.EMPTY
    owner_detected: bool = False
    num_faces: int = 0
    last_detection_time: float = 0.0
    owner_name: Optional[str] = None
    intruder_active: bool = False
    empty_since: float = 0.0


class RoomPresenceService:
    """Monitors room presence and manages security."""

    def __init__(self):
        self.state = RoomState()
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._intruder_records: List[IntruderRecord] = []
        self._recording_intruder = False
        self._intruder_record_start: float = 0
        self._last_owner_greeting: float = 0
        self._callbacks: Dict[str, list] = {
            "owner_entered": [],
            "owner_left": [],
            "intruder_detected": [],
            "room_empty": [],
            "presence_changed": [],
        }
        self._detection_interval = 1.0  # seconds between face checks
        self._empty_threshold = settings.IDLE_TIMEOUT_SECONDS
        self._consecutive_empty = 0
        self._consecutive_owner = 0
        self._consecutive_unknown = 0
        self._stability_count = 3  # need N consecutive same results

        logger.info("Room presence service initialized")

    # ================================================================
    # Event Callbacks
    # ================================================================
    def on(self, event: str, callback):
        """Register a callback for presence events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    async def _emit(self, event: str, data=None):
        """Fire all callbacks for an event."""
        for cb in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(data)
                else:
                    cb(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    # ================================================================
    # Monitoring Loop
    # ================================================================
    async def start_monitoring(self):
        """Start the presence monitoring loop."""
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Room presence monitoring started")

    async def stop_monitoring(self):
        """Stop the presence monitoring loop."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Room presence monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop - checks for faces periodically."""
        while self._monitoring:
            try:
                await self._check_presence()
                await asyncio.sleep(self._detection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Presence monitor error: {e}")
                await asyncio.sleep(2)

    async def _check_presence(self):
        """Analyze current camera frame for presence."""
        frame = camera_service.get_latest_frame()
        if frame is None:
            return

        # Detect and recognize faces
        recognized = face_service.recognize_faces(frame)
        num_faces = len(recognized)
        now = time.time()

        owner_found = False
        unknown_found = False

        for info in recognized:
            if info.get("role") == "owner":
                owner_found = True
            elif info.get("name", "Unknown") == "Unknown":
                unknown_found = True

        # Update counters for stable detection
        if num_faces == 0:
            self._consecutive_empty += 1
            self._consecutive_owner = 0
            self._consecutive_unknown = 0
        elif owner_found:
            self._consecutive_owner += 1
            self._consecutive_empty = 0
            if not unknown_found:
                self._consecutive_unknown = 0
        elif unknown_found:
            self._consecutive_unknown += 1
            self._consecutive_empty = 0
            self._consecutive_owner = 0

        prev_state = self.state.presence

        # ---- Transition logic (require stability) ----
        if self._consecutive_empty >= self._stability_count:
            if self.state.presence != PresenceState.EMPTY:
                self.state.presence = PresenceState.EMPTY
                self.state.owner_detected = False
                self.state.num_faces = 0
                self.state.empty_since = now
                await self._on_room_empty()

        elif self._consecutive_owner >= self._stability_count:
            self.state.num_faces = num_faces
            self.state.last_detection_time = now

            if num_faces > 1 and unknown_found:
                self.state.presence = PresenceState.MULTIPLE_PEOPLE
                self.state.owner_detected = True
            elif not self.state.owner_detected:
                self.state.presence = PresenceState.OWNER_PRESENT
                self.state.owner_detected = True
                owner_info = next((r for r in recognized if r.get("role") == "owner"), {})
                self.state.owner_name = owner_info.get("name", settings.OWNER_NAME)
                await self._on_owner_entered()

        elif self._consecutive_unknown >= self._stability_count:
            if not self.state.owner_detected:
                self.state.presence = PresenceState.UNKNOWN_PERSON
                self.state.num_faces = num_faces
                self.state.last_detection_time = now
                self.state.intruder_active = True
                await self._on_intruder_detected(frame, recognized)

        if self.state.presence != prev_state:
            await self._emit("presence_changed", {
                "previous": prev_state,
                "current": self.state.presence,
                "num_faces": num_faces,
            })

    # ================================================================
    # Event Handlers
    # ================================================================
    async def _on_owner_entered(self):
        """Called when owner is detected entering the room."""
        now = time.time()
        should_greet = (now - self._last_owner_greeting) > settings.GREETING_COOLDOWN

        # Stop any intruder recording
        if self._recording_intruder:
            await self._stop_intruder_recording()

        logger.info(f"Owner ({self.state.owner_name}) entered the room")
        await self._emit("owner_entered", {
            "name": self.state.owner_name,
            "should_greet": should_greet,
            "time": datetime.now().isoformat(),
        })

        if should_greet:
            self._last_owner_greeting = now

    async def _on_room_empty(self):
        """Called when room becomes empty."""
        if self._recording_intruder:
            await self._stop_intruder_recording()

        self.state.intruder_active = False
        logger.info("Room is now empty")
        await self._emit("room_empty", {
            "time": datetime.now().isoformat(),
        })
        await self._emit("owner_left", {
            "time": datetime.now().isoformat(),
        })

    async def _on_intruder_detected(self, frame, recognized):
        """Called when unknown person detected without owner."""
        logger.warning("INTRUDER DETECTED in room!")

        # Capture intruder photo
        photo_path = face_service.capture_intruder(frame)

        # Start recording
        video_path = None
        if not self._recording_intruder:
            video_path = await self._start_intruder_recording()

        record = IntruderRecord(
            timestamp=datetime.now().isoformat(),
            photo_path=photo_path or "",
            video_path=video_path,
        )
        self._intruder_records.append(record)

        await self._emit("intruder_detected", {
            "photo_path": photo_path,
            "video_path": video_path,
            "num_faces": len(recognized),
            "time": datetime.now().isoformat(),
        })

    async def _start_intruder_recording(self) -> Optional[str]:
        """Start recording intruder activity."""
        self._recording_intruder = True
        self._intruder_record_start = time.time()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = os.path.join(settings.INTRUDER_DIR, f"intruder_{ts}.avi")
        camera_service.start_recording(video_path)
        logger.info(f"Started intruder recording: {video_path}")
        return video_path

    async def _stop_intruder_recording(self):
        """Stop intruder recording."""
        if self._recording_intruder:
            camera_service.stop_recording()
            duration = time.time() - self._intruder_record_start
            self._recording_intruder = False
            logger.info(f"Stopped intruder recording. Duration: {duration:.1f}s")

            if self._intruder_records:
                self._intruder_records[-1].duration_seconds = duration

    # ================================================================
    # Queries
    # ================================================================
    def get_state(self) -> Dict:
        return {
            "presence": self.state.presence.value,
            "owner_detected": self.state.owner_detected,
            "owner_name": self.state.owner_name,
            "num_faces": self.state.num_faces,
            "intruder_active": self.state.intruder_active,
            "empty_since": self.state.empty_since,
            "last_detection": self.state.last_detection_time,
        }

    def get_intruder_records(self) -> List[Dict]:
        return [
            {
                "timestamp": r.timestamp,
                "photo": r.photo_path,
                "video": r.video_path,
                "duration": r.duration_seconds,
                "summary": r.activity_summary,
            }
            for r in self._intruder_records
        ]

    def get_intruder_count(self) -> int:
        return len(self._intruder_records)

    @property
    def is_monitoring(self) -> bool:
        return self._monitoring


# Singleton
presence_service = RoomPresenceService()
