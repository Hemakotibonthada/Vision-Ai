"""
Jarvis AI - Camera Service
============================
Manages camera input from local webcam or ESP32-CAM.
Provides frames for face recognition and surveillance.
"""
import os
import time
import threading
import queue
from datetime import datetime
from typing import Optional, Callable

import cv2
import numpy as np
from loguru import logger

from jarvis.config import settings


class CameraService:
    """Manages camera capture from local or ESP32-CAM sources."""

    def __init__(self):
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._fps = 0.0
        self._last_fps_time = time.time()
        self._fps_count = 0
        self._source = "none"
        self._frame_callbacks: list = []
        self._recording = False
        self._video_writer: Optional[cv2.VideoWriter] = None

        logger.info("Camera service initialized")

    def start(self, source: str = "local") -> bool:
        """Start camera capture.
        
        Args:
            source: "local" for webcam, "esp32" for ESP32-CAM, or URL
        """
        if self._running:
            self.stop()

        self._source = source

        if source == "local":
            self._cap = cv2.VideoCapture(settings.CAMERA_INDEX)
            if self._cap and self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAMERA_WIDTH)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAMERA_HEIGHT)
                self._cap.set(cv2.CAP_PROP_FPS, settings.CAMERA_FPS)
                logger.info(f"Local camera opened (index {settings.CAMERA_INDEX})")
            else:
                logger.error("Failed to open local camera")
                return False
        elif source == "esp32":
            self._cap = None  # Will use HTTP requests
            logger.info(f"ESP32-CAM source: {settings.ESP32_CAM_URL}")
        else:
            self._cap = cv2.VideoCapture(source)
            if not self._cap or not self._cap.isOpened():
                logger.error(f"Failed to open camera source: {source}")
                return False

        self._running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        return True

    def stop(self):
        """Stop camera capture."""
        self._running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=3)
        if self._cap:
            self._cap.release()
            self._cap = None
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None
        self._recording = False
        logger.info("Camera stopped")

    def _capture_loop(self):
        """Background frame capture loop."""
        while self._running:
            try:
                frame = self._read_frame()
                if frame is not None:
                    with self._frame_lock:
                        self._frame = frame
                    self._frame_count += 1
                    self._update_fps()

                    # Notify callbacks
                    for cb in self._frame_callbacks:
                        try:
                            cb(frame)
                        except Exception as e:
                            logger.error(f"Frame callback error: {e}")

                    # Write to video if recording
                    if self._recording and self._video_writer:
                        self._video_writer.write(frame)
                else:
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"Capture error: {e}")
                time.sleep(1)

        logger.info("Capture loop ended")

    def _read_frame(self) -> Optional[np.ndarray]:
        """Read a single frame from the camera source."""
        if self._source == "esp32":
            return self._read_esp32_frame()

        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            return frame if ret else None
        return None

    def _read_esp32_frame(self) -> Optional[np.ndarray]:
        """Read frame from ESP32-CAM over HTTP."""
        try:
            import urllib.request
            resp = urllib.request.urlopen(settings.ESP32_CAM_URL, timeout=5)
            img_array = np.frombuffer(resp.read(), dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            logger.debug(f"ESP32-CAM read failed: {e}")
            return None

    def _update_fps(self):
        """Track FPS."""
        self._fps_count += 1
        elapsed = time.time() - self._last_fps_time
        if elapsed >= 1.0:
            self._fps = self._fps_count / elapsed
            self._fps_count = 0
            self._last_fps_time = time.time()

    # ================================================================
    # Frame Access
    # ================================================================
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame (thread-safe copy)."""
        with self._frame_lock:
            return self._frame.copy() if self._frame is not None else None

    def get_jpeg(self, quality: int = 80) -> Optional[bytes]:
        """Get latest frame as JPEG bytes."""
        frame = self.get_frame()
        if frame is not None:
            _, buffer = cv2.imencode(".jpg", frame,
                                     [cv2.IMWRITE_JPEG_QUALITY, quality])
            return buffer.tobytes()
        return None

    def on_frame(self, callback: Callable):
        """Register a callback for every new frame."""
        self._frame_callbacks.append(callback)

    # ================================================================
    # Recording
    # ================================================================
    def start_recording(self, filename: str = None) -> str:
        """Start recording video."""
        if self._recording:
            return self._current_recording_path

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.avi"

        filepath = os.path.join(settings.RECORDINGS_DIR, filename)
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self._video_writer = cv2.VideoWriter(
            filepath, fourcc, 20.0,
            (settings.CAMERA_WIDTH, settings.CAMERA_HEIGHT)
        )
        self._recording = True
        self._current_recording_path = filepath
        logger.info(f"Recording started: {filepath}")
        return filepath

    def stop_recording(self) -> Optional[str]:
        """Stop recording and return file path."""
        if not self._recording:
            return None

        self._recording = False
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None

        path = getattr(self, "_current_recording_path", None)
        logger.info(f"Recording stopped: {path}")
        return path

    def capture_snapshot(self, suffix: str = "") -> Optional[str]:
        """Capture a single snapshot."""
        frame = self.get_frame()
        if frame is None:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"snapshot_{suffix}_{timestamp}.jpg" if suffix else f"snapshot_{timestamp}.jpg"
        filepath = os.path.join(settings.RECORDINGS_DIR, filename)
        cv2.imwrite(filepath, frame)
        return filepath

    # ================================================================
    # Status
    # ================================================================
    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps(self) -> float:
        return round(self._fps, 1)

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "source": self._source,
            "fps": self.fps,
            "frame_count": self._frame_count,
            "recording": self._recording,
            "has_frame": self._frame is not None
        }


# Singleton
camera_service = CameraService()
