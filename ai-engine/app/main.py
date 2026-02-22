"""
Vision-AI Engine - Main Application Entry Point
Comprehensive AI-powered vision system with 425+ features
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base, async_session

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vision-ai")


# ---- WebSocket Manager ----
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel: str = "default"):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        logger.info(f"WebSocket connected to channel: {channel}")
    
    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        if channel in self.active_connections:
            self.active_connections[channel] = [
                c for c in self.active_connections[channel] if c != websocket
            ]
    
    async def send_personal(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict, channel: str = "default"):
        if channel in self.active_connections:
            dead = []
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead.append(connection)
            for d in dead:
                self.active_connections[channel].remove(d)
    
    async def broadcast_all(self, message: dict):
        for channel in self.active_connections:
            await self.broadcast(message, channel)
    
    @property
    def connection_count(self) -> int:
        return sum(len(v) for v in self.active_connections.values())


ws_manager = ConnectionManager()


# ---- Lifespan ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("Vision-AI Engine Starting...")
    logger.info("=" * 60)
    
    # Initialize database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
    
    # Create storage directories
    import os
    for d in [settings.UPLOAD_DIR, settings.MODEL_DIR, settings.DATASET_DIR]:
        os.makedirs(d, exist_ok=True)
    logger.info("Storage directories created")
    
    # Load AI models
    try:
        from app.services.detection_service import detection_service
        detection_service.load_model(settings.DEFAULT_MODEL)
        logger.info(f"Default model loaded: {settings.DEFAULT_MODEL}")
    except Exception as e:
        logger.warning(f"Could not load default model: {e}")
    
    # Start MQTT
    try:
        from app.services.mqtt_service import mqtt_service
        mqtt_service.connect()
        
        # Bridge MQTT to WebSocket
        def on_any_message(topic, payload):
            asyncio.create_task(ws_manager.broadcast({
                "type": "mqtt", "topic": topic, "data": payload,
                "timestamp": datetime.utcnow().isoformat()
            }, "mqtt"))
        
        mqtt_service.subscribe("vision-ai/#", on_any_message)
        logger.info("MQTT service connected")
    except Exception as e:
        logger.warning(f"MQTT not available: {e}")
    
    # Create default admin user if none exists
    try:
        from sqlalchemy import select
        from app.database import User
        async with async_session() as db:
            result = await db.execute(select(User).where(User.role == "admin"))
            if not result.scalar_one_or_none():
                from app.routes.auth_routes import _hash_password
                admin = User(
                    username="admin",
                    email="admin@vision-ai.local",
                    password_hash=_hash_password("admin123"),
                    role="admin",
                    is_active=True
                )
                db.add(admin)
                await db.commit()
                logger.info("Default admin user created (admin/admin123)")
    except Exception as e:
        logger.warning(f"Could not create default admin: {e}")
    
    logger.info("Vision-AI Engine Ready!")
    logger.info(f"API: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"Docs: http://{settings.HOST}:{settings.PORT}/docs")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Vision-AI Engine...")
    try:
        from app.services.mqtt_service import mqtt_service
        mqtt_service.disconnect()
    except Exception:
        pass
    await engine.dispose()
    logger.info("Shutdown complete")


# ---- Create App ----
app = FastAPI(
    title="Vision-AI Engine",
    description="Comprehensive AI-powered IoT Vision System with 425+ features",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Request Middleware ----
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start).total_seconds()
    if duration > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} ({duration:.2f}s)")
    return response


# ---- Error Handlers ----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )


# ---- Register Routers ----
from app.routes.detection_routes import router as detection_router
from app.routes.training_routes import router as training_router
from app.routes.analytics_routes import router as analytics_router
from app.routes.device_routes import router as device_router
from app.routes.auth_routes import router as auth_router
from app.routes.vision_routes import router as vision_router

app.include_router(detection_router, prefix="/api/v1")
app.include_router(training_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(device_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(vision_router, prefix="/api/v1")


# ---- WebSocket Endpoints ----
@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str = "default"):
    """WebSocket endpoint for real-time communication."""
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            
            if msg_type == "ping":
                await ws_manager.send_personal({"type": "pong", "timestamp": datetime.utcnow().isoformat()}, websocket)
            
            elif msg_type == "subscribe":
                # Subscribe to additional channels
                sub_channel = data.get("channel", "")
                if sub_channel:
                    await ws_manager.connect(websocket, sub_channel)
            
            elif msg_type == "detect":
                # Real-time detection request
                import base64
                image_data = data.get("image")
                if image_data:
                    import numpy as np
                    import cv2
                    img_bytes = base64.b64decode(image_data)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    from app.services.detection_service import detection_service
                    result = detection_service.detect(frame)
                    await ws_manager.send_personal({
                        "type": "detection_result", "data": result,
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
            
            elif msg_type == "mqtt_publish":
                # Publish to MQTT
                from app.services.mqtt_service import mqtt_service
                mqtt_service.publish(data.get("topic", ""), json.dumps(data.get("payload", {})))
            
            elif msg_type == "broadcast":
                await ws_manager.broadcast(data.get("message", {}), channel)
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, channel)


@app.websocket("/ws/stream/{device_id}")
async def stream_endpoint(websocket: WebSocket, device_id: str):
    """WebSocket endpoint for camera stream relay."""
    await ws_manager.connect(websocket, f"stream_{device_id}")
    try:
        while True:
            data = await websocket.receive_bytes()
            # Broadcast frame to all viewers
            for conn in ws_manager.active_connections.get(f"stream_{device_id}", []):
                if conn != websocket:
                    try:
                        await conn.send_bytes(data)
                    except Exception:
                        pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, f"stream_{device_id}")


# ---- Root Endpoints ----
@app.get("/")
async def root():
    """API root with system info."""
    return {
        "name": "Vision-AI Engine",
        "version": "1.0.0",
        "features": 425,
        "status": "running",
        "docs": "/docs",
        "websocket": "/ws/{channel}",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/info")
async def api_info():
    """API information and available endpoints."""
    return {
        "version": "1.0.0",
        "endpoints": {
            "detection": "/api/v1/detect/*",
            "training": "/api/v1/training/*",
            "analytics": "/api/v1/analytics/*",
            "devices": "/api/v1/devices/*",
            "events": "/api/v1/events/*",
            "alerts": "/api/v1/alerts/*",
            "zones": "/api/v1/zones/*",
            "auth": "/api/v1/auth/*",
            "admin": "/api/v1/admin/*",
            "system": "/api/v1/system/*"
        },
        "websocket_channels": [
            "default", "mqtt", "detections", "alerts", "stream_{device_id}"
        ],
        "ws_connections": ws_manager.connection_count
    }


@app.get("/api/v1/ws/status")
async def ws_status():
    """WebSocket connection status."""
    return {
        "total_connections": ws_manager.connection_count,
        "channels": {k: len(v) for k, v in ws_manager.active_connections.items()}
    }


# ---- Static Files ----
import os
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ---- Run ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1,
        log_level=settings.LOG_LEVEL.lower()
    )
