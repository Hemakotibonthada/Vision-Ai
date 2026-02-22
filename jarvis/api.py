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
from jarvis.services.mqtt_bridge_service import MQTTBridgeService
from jarvis.services.esp32_manager_service import ESP32ManagerService

# Initialize MQTT bridge and ESP32 manager
mqtt_bridge = MQTTBridgeService(
    broker=settings.MQTT_BROKER,
    port=settings.MQTT_PORT,
    username=settings.MQTT_USERNAME,
    password=settings.MQTT_PASSWORD,
    client_id=settings.MQTT_CLIENT_ID,
)
esp32_manager = ESP32ManagerService(mqtt_bridge=mqtt_bridge)

# Link services
home_service.set_mqtt_bridge(mqtt_bridge)
home_service.set_esp32_manager(esp32_manager)


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

    # Start MQTT bridge
    mqtt_bridge.connect()

    # Register MQTT event handlers for Jarvis brain
    mqtt_bridge.register_handler("intruder", lambda data: asyncio.create_task(
        jarvis_brain._transition(JarvisState.INTRUDER_ALERT, f"MQTT intruder: {data.get('reason', 'unknown')}")
    ))
    mqtt_bridge.register_handler("door", lambda data: asyncio.create_task(
        ws_manager.broadcast({"type": "door_event", "data": data})
    ))
    mqtt_bridge.register_handler("motion", lambda data: asyncio.create_task(
        ws_manager.broadcast({"type": "motion_event", "data": data})
    ))
    mqtt_bridge.register_handler("person_detected", lambda data: asyncio.create_task(
        ws_manager.broadcast({"type": "person_detected", "data": data})
    ))
    mqtt_bridge.register_handler("face_identified", lambda data: asyncio.create_task(
        ws_manager.broadcast({"type": "face_identified", "data": data})
    ))
    mqtt_bridge.register_handler("heartbeat", lambda data: 
        esp32_manager.update_device_from_heartbeat(data)
    )

    # Start the Jarvis brain
    await jarvis_brain.start()


@app.on_event("shutdown")
async def shutdown():
    mqtt_bridge.disconnect()
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
# ESP32 Device Management Routes
# ================================================================
@app.get("/api/esp32/devices")
async def get_devices():
    """Get all registered ESP32 devices and their health."""
    return esp32_manager.get_device_health()


@app.get("/api/esp32/summary")
async def get_esp32_summary():
    """Get a high-level summary of all ESP32 devices."""
    return esp32_manager.get_summary()


@app.get("/api/esp32/health")
async def esp32_health_check():
    """Ping all ESP32 devices."""
    return await esp32_manager.health_check()


@app.get("/api/esp32/mqtt/stats")
async def mqtt_stats():
    """Get MQTT bridge statistics."""
    return mqtt_bridge.get_stats()


@app.get("/api/esp32/mqtt/devices")
async def mqtt_devices():
    """Get devices tracked by MQTT bridge."""
    return mqtt_bridge.get_all_devices()


@app.get("/api/esp32/mqtt/messages")
async def mqtt_messages(count: int = Query(50, ge=1, le=200), topic: str = Query(None)):
    """Get recent MQTT messages."""
    return mqtt_bridge.get_recent_messages(count, topic)


# ---- Server Control ----
@app.get("/api/esp32/server/status")
async def esp32_server_status():
    """Get ESP32 server status."""
    return await esp32_manager.get_server_status() or {"error": "Server unreachable"}


@app.get("/api/esp32/server/sensors")
async def esp32_server_sensors():
    """Get sensor readings from ESP32 server."""
    return await esp32_manager.get_sensors() or {"error": "unavailable"}


@app.get("/api/esp32/server/heartbeat")
async def esp32_server_heartbeat():
    """Get Jarvis heartbeat from ESP32 server."""
    return await esp32_manager.get_heartbeat() or {"error": "unavailable"}


@app.post("/api/esp32/server/relay/{relay_id}")
async def esp32_set_relay(relay_id: int, state: bool = Query(True)):
    """Control a relay on the ESP32 server."""
    result = await esp32_manager.set_relay(relay_id, state)
    return result or {"error": "failed"}


@app.post("/api/esp32/server/relay/{relay_id}/toggle")
async def esp32_toggle_relay(relay_id: int):
    """Toggle a relay on the ESP32 server."""
    return await esp32_manager.toggle_relay(relay_id) or {"error": "failed"}


@app.post("/api/esp32/server/relays/all")
async def esp32_all_relays(state: bool = Query(True)):
    """Set all relays."""
    return await esp32_manager.set_all_relays(state) or {"error": "failed"}


@app.get("/api/esp32/server/door")
async def esp32_door_status():
    """Get door sensor status."""
    return await esp32_manager.get_door_status() or {"error": "unavailable"}


@app.post("/api/esp32/server/lock")
async def esp32_set_lock(locked: bool = Query(True)):
    """Control the servo lock."""
    return await esp32_manager.set_lock(locked) or {"error": "failed"}


@app.post("/api/esp32/server/lock/toggle")
async def esp32_toggle_lock():
    """Toggle the lock."""
    return await esp32_manager.toggle_lock() or {"error": "failed"}


@app.get("/api/esp32/server/schedules")
async def esp32_get_schedules():
    """Get all schedules."""
    return await esp32_manager.get_schedules() or {"error": "unavailable"}


@app.post("/api/esp32/server/schedule/add")
async def esp32_add_schedule(
    relay: int = Query(...),
    hour: int = Query(...),
    minute: int = Query(...),
    action: int = Query(1),
    days: int = Query(0x7F),
    repeat: int = Query(1),
):
    """Add a new schedule."""
    return await esp32_manager.add_schedule(relay, hour, minute, action, days, repeat) or {"error": "failed"}


@app.post("/api/esp32/server/schedule/delete/{schedule_id}")
async def esp32_delete_schedule(schedule_id: int):
    """Delete a schedule."""
    return await esp32_manager.delete_schedule(schedule_id) or {"error": "failed"}


@app.post("/api/esp32/server/buzz")
async def esp32_buzz(pattern: str = Query("alert")):
    """Trigger buzzer."""
    return await esp32_manager.buzz(pattern) or {"error": "failed"}


# ---- Camera Control ----
@app.get("/api/esp32/camera/status")
async def esp32_cam_status():
    """Get ESP32-CAM status."""
    return await esp32_manager.get_camera_status() or {"error": "unavailable"}


@app.get("/api/esp32/camera/jarvis")
async def esp32_cam_jarvis_status():
    """Get Jarvis-specific camera status."""
    return await esp32_manager.get_jarvis_cam_status() or {"error": "unavailable"}


@app.get("/api/esp32/camera/detect")
async def esp32_cam_detect():
    """Trigger a capture + AI detection on the camera."""
    return await esp32_manager.trigger_detection() or {"error": "failed"}


@app.get("/api/esp32/camera/capture")
async def esp32_cam_capture():
    """Capture a JPEG image from the camera."""
    image_data = await esp32_manager.capture_image()
    if image_data:
        return StreamingResponse(
            iter([image_data]),
            media_type="image/jpeg",
            headers={"Content-Disposition": "inline; filename=capture.jpg"}
        )
    raise HTTPException(503, "Camera unavailable")


@app.get("/api/esp32/camera/stream-url")
async def esp32_cam_stream_url():
    """Get the camera MJPEG stream URL."""
    url = await esp32_manager.get_stream_url()
    return {"stream_url": url}


# ---- MQTT-based commands (faster, fire-and-forget) ----
@app.post("/api/esp32/mqtt/relay")
async def mqtt_relay(relay: int = Query(...), state: bool = Query(True)):
    """Control relay via MQTT (fire-and-forget)."""
    success = mqtt_bridge.set_relay(relay, state)
    return {"sent": success}


@app.post("/api/esp32/mqtt/lock")
async def mqtt_lock(locked: bool = Query(True)):
    """Control lock via MQTT."""
    success = mqtt_bridge.set_lock(locked)
    return {"sent": success}


@app.post("/api/esp32/mqtt/capture")
async def mqtt_capture(context: str = Query("jarvis")):
    """Trigger camera capture via MQTT."""
    success = mqtt_bridge.trigger_capture(context)
    return {"sent": success}


@app.post("/api/esp32/mqtt/patrol")
async def mqtt_patrol(enabled: bool = Query(True)):
    """Start/stop patrol mode via MQTT."""
    if enabled:
        success = mqtt_bridge.start_patrol()
    else:
        success = mqtt_bridge.stop_patrol()
    return {"sent": success}


@app.post("/api/esp32/mqtt/intruder-mode")
async def mqtt_intruder_mode(enabled: bool = Query(True)):
    """Enable/disable intruder mode via MQTT."""
    success = mqtt_bridge.set_intruder_mode(enabled)
    return {"sent": success}


@app.post("/api/esp32/mqtt/identify")
async def mqtt_identify():
    """Request face identification via MQTT."""
    success = mqtt_bridge.request_identify()
    return {"sent": success}


@app.post("/api/esp32/mqtt/scene")
async def mqtt_scene(name: str = Query(...)):
    """Activate a scene via MQTT."""
    success = mqtt_bridge.activate_scene(name)
    return {"sent": success}


@app.post("/api/esp32/mqtt/buzz")
async def mqtt_buzz(pattern: str = Query("alert")):
    """Trigger buzzer via MQTT."""
    success = mqtt_bridge.buzz_alert(pattern)
    return {"sent": success}


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
