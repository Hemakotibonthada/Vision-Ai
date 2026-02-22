"""
Vision-AI Detection Service
Features: Object detection, classification, face detection, tracking
"""
import io
import os
import time
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import numpy as np
import cv2
from PIL import Image
import torch
from loguru import logger

from app.config import settings


class DetectionService:
    """Main AI detection service with multiple model support."""

    def __init__(self):
        self.models = {}
        self.active_model = None
        self.active_model_name = None
        self.device = self._get_device()
        self.class_names = []
        self.inference_count = 0
        self.total_inference_time = 0
        self.detection_history = []
        logger.info(f"Detection service initialized on {self.device}")

    def _get_device(self) -> str:
        if settings.DEVICE == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return settings.DEVICE

    # Feature 111: YOLOv8 Object Detection
    async def load_yolo_model(self, model_name: str = "yolov8n") -> bool:
        try:
            from ultralytics import YOLO
            model_path = os.path.join(settings.MODEL_DIR, f"{model_name}.pt")

            if os.path.exists(model_path):
                model = YOLO(model_path)
            else:
                model = YOLO(f"{model_name}.pt")
                os.makedirs(settings.MODEL_DIR, exist_ok=True)

            self.models[model_name] = model
            self.active_model = model
            self.active_model_name = model_name
            self.class_names = model.names if hasattr(model, 'names') else []
            logger.info(f"YOLO model loaded: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return False

    # Feature 112: SSD MobileNet Detection
    async def load_ssd_model(self) -> bool:
        try:
            model = torch.hub.load('NVIDIA/DeepLearningExamples:torchhub', 'nvidia_ssd', pretrained=True)
            model.eval().to(self.device)
            self.models["ssd_mobilenet"] = model
            logger.info("SSD MobileNet loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load SSD: {e}")
            return False

    # Feature 113: Image Classification
    async def load_classification_model(self, model_name: str = "resnet50") -> bool:
        try:
            import torchvision.models as models
            if model_name == "resnet50":
                model = models.resnet50(pretrained=True)
            elif model_name == "efficientnet":
                model = models.efficientnet_b0(pretrained=True)
            else:
                model = models.mobilenet_v3_small(pretrained=True)

            model.eval().to(self.device)
            self.models[f"classifier_{model_name}"] = model
            logger.info(f"Classification model loaded: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load classifier: {e}")
            return False

    # Feature 141: Detect objects in image
    async def detect(self, image_bytes: bytes, model_name: str = None,
                     confidence: float = None, nms: float = None) -> Dict:
        if confidence is None:
            confidence = settings.CONFIDENCE_THRESHOLD
        if nms is None:
            nms = settings.NMS_THRESHOLD

        model = self.models.get(model_name, self.active_model)
        if model is None:
            await self.load_yolo_model()
            model = self.active_model

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image"}

        h, w = img.shape[:2]

        # Run inference
        start_time = time.time()
        results = model(img, conf=confidence, iou=nms, max_det=settings.MAX_DETECTIONS)
        inference_time = (time.time() - start_time) * 1000

        # Parse results
        detections = []
        class_counts = {}

        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    class_name = model.names[cls_id] if hasattr(model, 'names') else str(cls_id)

                    detection = {
                        "class": class_name,
                        "class_id": cls_id,
                        "confidence": round(conf, 4),
                        "bbox": {
                            "x1": round(x1, 2), "y1": round(y1, 2),
                            "x2": round(x2, 2), "y2": round(y2, 2),
                            "width": round(x2 - x1, 2),
                            "height": round(y2 - y1, 2),
                            "center_x": round((x1 + x2) / 2, 2),
                            "center_y": round((y1 + y2) / 2, 2)
                        },
                        "area": round((x2 - x1) * (y2 - y1), 2)
                    }
                    detections.append(detection)

                    class_counts[class_name] = class_counts.get(class_name, 0) + 1

        # Update stats
        self.inference_count += 1
        self.total_inference_time += inference_time

        result = {
            "detections": detections,
            "total_objects": len(detections),
            "class_counts": class_counts,
            "classes_detected": list(class_counts.keys()),
            "inference_time_ms": round(inference_time, 2),
            "model": model_name or self.active_model_name,
            "image_size": {"width": w, "height": h},
            "confidence_threshold": confidence,
            "nms_threshold": nms,
            "timestamp": datetime.utcnow().isoformat(),
            "device": self.device
        }

        self.detection_history.append({
            "total": len(detections),
            "classes": class_counts,
            "time_ms": round(inference_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep last 1000 results
        if len(self.detection_history) > 1000:
            self.detection_history = self.detection_history[-1000:]

        return result

    # Feature 125: Object counting
    async def count_objects(self, image_bytes: bytes, target_class: str = None) -> Dict:
        result = await self.detect(image_bytes)
        if target_class:
            count = result["class_counts"].get(target_class, 0)
            return {"class": target_class, "count": count, "total": result["total_objects"]}
        return {"counts": result["class_counts"], "total": result["total_objects"]}

    # Feature 126: Object tracking
    async def track_objects(self, image_bytes: bytes) -> Dict:
        model = self.active_model
        if model is None:
            await self.load_yolo_model()
            model = self.active_model

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        start_time = time.time()
        results = model.track(img, persist=True, conf=settings.CONFIDENCE_THRESHOLD)
        inference_time = (time.time() - start_time) * 1000

        tracked = []
        for result in results:
            boxes = result.boxes
            if boxes is not None and boxes.id is not None:
                for box, track_id in zip(boxes, boxes.id):
                    tracked.append({
                        "track_id": int(track_id),
                        "class": model.names[int(box.cls[0])],
                        "confidence": round(float(box.conf[0]), 4),
                        "bbox": box.xyxy[0].tolist()
                    })

        return {
            "tracked_objects": tracked,
            "total_tracked": len(tracked),
            "inference_time_ms": round(inference_time, 2)
        }

    # Feature 166: Feature extraction
    async def extract_features(self, image_bytes: bytes) -> Dict:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Use a pre-trained model for feature extraction
        import torchvision.transforms as transforms
        import torchvision.models as models

        model = models.resnet50(pretrained=True)
        model = torch.nn.Sequential(*list(model.children())[:-1])
        model.eval()

        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        tensor = transform(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).unsqueeze(0)

        with torch.no_grad():
            features = model(tensor).squeeze().numpy()

        return {
            "features": features.tolist()[:50],  # First 50 features
            "feature_dim": len(features),
            "norm": float(np.linalg.norm(features))
        }

    # Feature 186: Heatmap generation
    async def generate_heatmap(self, detections_list: List[Dict], width: int = 640, height: int = 480) -> bytes:
        heatmap = np.zeros((height, width), dtype=np.float32)

        for det in detections_list:
            for d in det.get("detections", []):
                bbox = d.get("bbox", {})
                cx = int(bbox.get("center_x", 0))
                cy = int(bbox.get("center_y", 0))
                if 0 <= cx < width and 0 <= cy < height:
                    cv2.circle(heatmap, (cx, cy), 30, 1.0, -1)

        heatmap = cv2.GaussianBlur(heatmap, (51, 51), 0)
        heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8) if heatmap.max() > 0 else heatmap.astype(np.uint8)
        heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

        _, buffer = cv2.imencode('.jpg', heatmap_color)
        return buffer.tobytes()

    # Feature 181: GradCAM interpretability
    async def grad_cam(self, image_bytes: bytes, target_class: int = None) -> bytes:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_resized = cv2.resize(img, (224, 224))

        import torchvision.transforms as transforms
        import torchvision.models as models

        model = models.resnet50(pretrained=True)
        model.eval()

        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        input_tensor = transform(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).unsqueeze(0)
        input_tensor.requires_grad_(True)

        # Forward pass
        target_layer = model.layer4[-1]
        activations = {}
        gradients = {}

        def forward_hook(module, input, output):
            activations['value'] = output

        def backward_hook(module, grad_in, grad_out):
            gradients['value'] = grad_out[0]

        fh = target_layer.register_forward_hook(forward_hook)
        bh = target_layer.register_full_backward_hook(backward_hook)

        output = model(input_tensor)
        if target_class is None:
            target_class = output.argmax().item()

        model.zero_grad()
        output[0, target_class].backward()

        grads = gradients['value'].detach()
        acts = activations['value'].detach()

        weights = grads.mean(dim=[2, 3], keepdim=True)
        cam = (weights * acts).sum(dim=1, keepdim=True)
        cam = torch.relu(cam)
        cam = cam.squeeze().numpy()
        cam = cv2.resize(cam, (224, 224))
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        cam = (cam * 255).astype(np.uint8)

        heatmap = cv2.applyColorMap(cam, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(img_resized, 0.5, heatmap, 0.5, 0)

        fh.remove()
        bh.remove()

        _, buffer = cv2.imencode('.jpg', overlay)
        return buffer.tobytes()

    # Statistics
    def get_stats(self) -> Dict:
        avg_time = self.total_inference_time / max(self.inference_count, 1)
        return {
            "inference_count": self.inference_count,
            "avg_inference_time_ms": round(avg_time, 2),
            "total_inference_time_ms": round(self.total_inference_time, 2),
            "loaded_models": list(self.models.keys()),
            "active_model": self.active_model_name,
            "device": self.device,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }


# Singleton instance
detection_service = DetectionService()
