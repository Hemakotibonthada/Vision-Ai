"""Vision-AI Routes Package"""
from app.routes.detection_routes import router as detection_router
from app.routes.training_routes import router as training_router
from app.routes.analytics_routes import router as analytics_router
from app.routes.device_routes import router as device_router
from app.routes.auth_routes import router as auth_router

__all__ = [
    "detection_router",
    "training_router",
    "analytics_router",
    "device_router",
    "auth_router"
]
