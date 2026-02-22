"""
Jarvis AI - API Routes
========================
FastAPI REST + WebSocket endpoints for the Jarvis system.
"""
import asyncio
import os
import json
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from jarvis.config import settings
from jarvis.services.jarvis_brain import jarvis_brain, JarvisState
from jarvis.services.face_recognition_service import face_service
from jarvis.services.voice_service import voice_service
from jarvis.services.camera_service import camera_service
from jarvis.services.room_presence_service import presence_service
from jarvis.services.home_automation_service import home_service
from jarvis.services.vision_integration_service import vision_service
from jarvis.services.learning_service import learning_service
from jarvis.services.command_processor import command_processor


# ================================================================
# FastAPI App
# ================================================================
app = FastAPI(
    title="Jarvis AI",
    description="Intelligent Home AI Assistant with Face Recognition, Voice Control, and Security",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve dashboard
DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")


@app.get("/dashboard")
async def dashboard():
    return FileResponse(DASHBOARD_PATH, media_type="text/html")


# ================================================================
# WebSocket Manager
# ================================================================
class WSManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = WSManager()


# ================================================================
# Lifecycle
# ================================================================
@app.on_event("startup")
async def startup():
    logger.info("Jarvis API server starting...")

    # Register state change callback for WebSocket broadcast
    async def on_state_change(old, new, reason):
        await ws_manager.broadcast({
            "type": "state_change",
            "data": {"from": old, "to": new, "reason": reason},
        })

    jarvis_brain.on_state_change(on_state_change)

    # Start the Jarvis brain
    await jarvis_brain.start()


@app.on_event("shutdown")
async def shutdown():
    await jarvis_brain.stop()
    logger.info("Jarvis API server stopped")


# ================================================================
# System Routes
# ================================================================
@app.get("/")
async def root():
    return {
        "name": "Jarvis AI",
        "version": "1.0.0",
        "state": jarvis_brain.state.value,
        "uptime": jarvis_brain.state_info.get("stats", {}).get("uptime_seconds", 0),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "state": jarvis_brain.state.value}


@app.get("/api/status")
async def system_status():
    return {
        "jarvis": jarvis_brain.state_info,
        "room": presence_service.get_state(),
        "camera_active": camera_service._running,
        "monitoring_active": presence_service.is_monitoring,
        "vision_api": vision_service.is_available,
        "learning": learning_service.get_summary(),
    }


@app.get("/api/events")
async def event_log(limit: int = Query(50, ge=1, le=500)):
    return jarvis_brain.get_event_log(limit)


# ================================================================
# Command Routes
# ================================================================
@app.post("/api/command")
async def send_command(command: str = Query(...)):
    """Send a text command to Jarvis."""
    response = await jarvis_brain.process_voice_command(command)
    return {"command": command, "response": response, "state": jarvis_brain.state.value}


@app.post("/api/command/parse")
async def parse_command(command: str = Query(...)):
    """Parse a command without executing it."""
    parsed = command_processor.parse(command)
    return parsed


@app.get("/api/command/help")
async def command_help():
    return {"help": command_processor.get_help_text()}


@app.get("/api/command/history")
async def command_history(limit: int = Query(20)):
    return command_processor.get_history(limit)


# ================================================================
# Face Recognition Routes
# ================================================================
@app.post("/api/face/register-owner")
async def register_owner_face(
    name: str = Query(default=None),
    file: UploadFile = File(...)
):
    """Register the owner's face from an uploaded image."""
    import cv2
    import numpy as np

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(400, "Invalid image")

    owner_name = name or settings.OWNER_NAME
    success = face_service.register_owner(owner_name, frame)

    if success:
        return {"status": "success", "name": owner_name}
    raise HTTPException(400, "No face detected in image")


@app.post("/api/face/register-owner-camera")
async def register_owner_from_camera(name: str = Query(default=None)):
    """Register the owner's face from the live camera."""
    frame = camera_service.get_latest_frame()
    if frame is None:
        raise HTTPException(503, "Camera not available")

    owner_name = name or settings.OWNER_NAME
    success = face_service.register_owner(owner_name, frame)

    if success:
        return {"status": "success", "name": owner_name}
    raise HTTPException(400, "No face detected")


@app.post("/api/face/register-person")
async def register_known_person(
    name: str = Query(...),
    role: str = Query(default="known"),
    file: UploadFile = File(...)
):
    """Register a known person's face."""
    import cv2
    import numpy as np

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(400, "Invalid image")

    success = face_service.register_known_person(name, role, frame)
    if success:
        return {"status": "success", "name": name, "role": role}
    raise HTTPException(400, "No face detected in image")


@app.get("/api/face/recognize")
async def recognize_current():
    """Recognize faces in the current camera frame."""
    frame = camera_service.get_latest_frame()
    if frame is None:
        raise HTTPException(503, "Camera not available")

    results = face_service.recognize_faces(frame)
    return {"faces": results, "count": len(results)}


@app.get("/api/face/owner")
async def get_owner_info():
    info = face_service.get_owner_info()
    if info:
        return info
    raise HTTPException(404, "No owner registered")


# ================================================================
# Camera Routes
# ================================================================
@app.get("/api/camera/snapshot")
async def camera_snapshot():
    """Get current camera frame as JPEG."""
    jpeg = camera_service.get_jpeg()
    if jpeg is None:
        raise HTTPException(503, "Camera not available")
    return StreamingResponse(
        iter([jpeg]),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/api/camera/record/start")
async def start_recording():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(settings.RECORDINGS_DIR, f"manual_{ts}.avi")
    camera_service.start_recording(path)
    return {"status": "recording", "path": path}


@app.post("/api/camera/record/stop")
async def stop_recording():
    camera_service.stop_recording()
    return {"status": "stopped"}


@app.get("/api/camera/stream")
async def camera_stream():
    """MJPEG stream endpoint."""
    async def generate():
        while True:
            jpeg = camera_service.get_jpeg()
            if jpeg:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" +
                    jpeg +
                    b"\r\n"
                )
            await asyncio.sleep(0.05)  # ~20fps

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ================================================================
# Security Routes
# ================================================================
@app.get("/api/security/status")
async def security_status():
    return {
        "room": presence_service.get_state(),
        "intruder_count": presence_service.get_intruder_count(),
        "monitoring": presence_service.is_monitoring,
    }


@app.get("/api/security/intruders")
async def intruder_records():
    return presence_service.get_intruder_records()


@app.get("/api/security/intruder-photos")
async def intruder_photos():
    """List all intruder captured photos."""
    photos = []
    if os.path.exists(settings.INTRUDER_DIR):
        for f in sorted(os.listdir(settings.INTRUDER_DIR)):
            if f.endswith((".jpg", ".png")):
                photos.append({
                    "filename": f,
                    "path": os.path.join(settings.INTRUDER_DIR, f),
                    "url": f"/api/security/intruder-photo/{f}",
                })
    return photos


@app.get("/api/security/intruder-photo/{filename}")
async def get_intruder_photo(filename: str):
    path = os.path.join(settings.INTRUDER_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")
    raise HTTPException(404, "Photo not found")


# ================================================================
# Home Automation Routes
# ================================================================
@app.post("/api/home/relay")
async def control_relay(relay: int = Query(..., ge=1, le=8), state: bool = Query(...)):
    result = await home_service.set_relay(relay, state)
    return result


@app.post("/api/home/relay/room")
async def control_room(room: str = Query(...), state: bool = Query(...)):
    result = await home_service.set_relay_by_room(room, state)
    return result


@app.post("/api/home/relay/all")
async def control_all(state: bool = Query(...)):
    result = await home_service.set_all_relays(state)
    return result


@app.get("/api/home/status")
async def home_status():
    return await home_service.get_relay_status()


@app.get("/api/home/sensors")
async def home_sensors():
    return await home_service.get_sensors()


@app.post("/api/home/command")
async def home_command(command: str = Query(...)):
    response = await home_service.process_command(command)
    return {"command": command, "response": response}


# ================================================================
# Learning Routes
# ================================================================
@app.get("/api/learning/summary")
async def learning_summary():
    return learning_service.get_summary()


@app.post("/api/learning/cycle")
async def run_learning():
    return learning_service.run_learning_cycle()


# ================================================================
# Voice Routes
# ================================================================
@app.post("/api/voice/speak")
async def speak_text(text: str = Query(...)):
    voice_service.speak(text)
    return {"status": "speaking", "text": text}


@app.post("/api/voice/greet")
async def greet(name: str = Query(default=None)):
    voice_service.greet_owner(name or settings.OWNER_NAME)
    return {"status": "greeted"}


# ================================================================
# State Control Routes
# ================================================================
@app.post("/api/state/sleep")
async def go_to_sleep():
    await jarvis_brain._transition(JarvisState.SLEEPING, "API request")
    return {"state": jarvis_brain.state.value}


@app.post("/api/state/wake")
async def wake_up():
    await jarvis_brain._transition(JarvisState.OWNER_PRESENT, "API request")
    return {"state": jarvis_brain.state.value}


@app.post("/api/state/listen")
async def start_listening():
    await jarvis_brain._transition(JarvisState.LISTENING, "API request")
    return {"state": jarvis_brain.state.value}


# ================================================================
# WebSocket
# ================================================================
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    logger.info("WebSocket client connected")

    # Send initial state
    await ws.send_json({
        "type": "init",
        "data": {
            "state": jarvis_brain.state.value,
            "room": presence_service.get_state(),
            "stats": jarvis_brain.state_info.get("stats", {}),
        },
    })

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "command":
                response = await jarvis_brain.process_voice_command(msg.get("text", ""))
                await ws.send_json({
                    "type": "command_response",
                    "data": {"response": response, "state": jarvis_brain.state.value},
                })

            elif msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        ws_manager.disconnect(ws)
        logger.error(f"WebSocket error: {e}")
