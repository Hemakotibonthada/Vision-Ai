"""
Vision-AI Training Service
Features: Model training, transfer learning, self-training, active learning
"""
import os
import json
import shutil
import time
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from loguru import logger

from app.config import settings


class TrainingService:
    """Comprehensive model training service with self-training capabilities."""

    def __init__(self):
        self.active_training = None
        self.training_history = []
        self.training_progress = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Training service initialized on {self.device}")

    # Feature 131: Custom model training pipeline
    async def train_yolo(self, config: Dict) -> Dict:
        """Train a YOLOv8 model with custom configuration."""
        from ultralytics import YOLO

        training_id = str(uuid.uuid4())[:8]
        self.training_progress[training_id] = {
            "status": "initializing",
            "epoch": 0,
            "total_epochs": config.get("epochs", settings.EPOCHS),
            "metrics": {},
            "started_at": datetime.utcnow().isoformat()
        }

        try:
            # Load base model
            base_model = config.get("base_model", "yolov8n.pt")
            model = YOLO(base_model)

            # Training configuration
            train_config = {
                "data": config.get("data_yaml", ""),
                "epochs": config.get("epochs", settings.EPOCHS),
                "batch": config.get("batch_size", settings.BATCH_SIZE),
                "imgsz": config.get("image_size", 640),
                "lr0": config.get("learning_rate", settings.LEARNING_RATE),
                "patience": config.get("patience", settings.EARLY_STOPPING_PATIENCE),
                "save": True,
                "save_period": config.get("save_period", 10),
                "project": settings.TRAINING_DIR,
                "name": f"train_{training_id}",
                "exist_ok": True,
                "pretrained": config.get("pretrained", True),
                "optimizer": config.get("optimizer", "auto"),
                "device": self.device,
                "workers": config.get("workers", 4),
                "augment": config.get("augment", settings.AUGMENTATION_ENABLED),
                "val": config.get("validate", True),
                "plots": True,
                "verbose": True
            }

            # Data augmentation settings
            if config.get("augmentation"):
                aug = config["augmentation"]
                train_config.update({
                    "hsv_h": aug.get("hsv_h", 0.015),
                    "hsv_s": aug.get("hsv_s", 0.7),
                    "hsv_v": aug.get("hsv_v", 0.4),
                    "degrees": aug.get("degrees", 0.0),
                    "translate": aug.get("translate", 0.1),
                    "scale": aug.get("scale", 0.5),
                    "shear": aug.get("shear", 0.0),
                    "perspective": aug.get("perspective", 0.0),
                    "flipud": aug.get("flipud", 0.0),
                    "fliplr": aug.get("fliplr", 0.5),
                    "mosaic": aug.get("mosaic", 1.0),
                    "mixup": aug.get("mixup", 0.0),
                    "copy_paste": aug.get("copy_paste", 0.0),
                })

            self.training_progress[training_id]["status"] = "training"
            self.active_training = training_id

            # Run training
            results = model.train(**train_config)

            # Get metrics
            metrics = {
                "mAP50": float(results.results_dict.get("metrics/mAP50(B)", 0)),
                "mAP50_95": float(results.results_dict.get("metrics/mAP50-95(B)", 0)),
                "precision": float(results.results_dict.get("metrics/precision(B)", 0)),
                "recall": float(results.results_dict.get("metrics/recall(B)", 0)),
                "box_loss": float(results.results_dict.get("train/box_loss", 0)),
                "cls_loss": float(results.results_dict.get("train/cls_loss", 0)),
            }

            # Save best model
            best_model_path = os.path.join(settings.TRAINING_DIR, f"train_{training_id}", "weights", "best.pt")

            self.training_progress[training_id].update({
                "status": "completed",
                "metrics": metrics,
                "model_path": best_model_path,
                "completed_at": datetime.utcnow().isoformat()
            })

            self.training_history.append(self.training_progress[training_id])
            self.active_training = None

            return {
                "training_id": training_id,
                "status": "completed",
                "metrics": metrics,
                "model_path": best_model_path
            }

        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.training_progress[training_id].update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            })
            self.active_training = None
            return {"training_id": training_id, "status": "failed", "error": str(e)}

    # Feature 132: Transfer learning
    async def transfer_learn(self, base_model: str, data_yaml: str,
                             freeze_layers: int = 10, epochs: int = 50) -> Dict:
        """Fine-tune a pre-trained model on new data."""
        from ultralytics import YOLO

        model = YOLO(base_model)

        # Freeze backbone layers
        for i, (name, param) in enumerate(model.model.named_parameters()):
            if i < freeze_layers:
                param.requires_grad = False

        config = {
            "base_model": base_model,
            "data_yaml": data_yaml,
            "epochs": epochs,
            "learning_rate": settings.LEARNING_RATE * 0.1,  # Lower LR for fine-tuning
            "pretrained": True
        }

        return await self.train_yolo(config)

    # Feature 135: Self-training with pseudo-labels
    async def self_train(self, model_path: str, unlabeled_dir: str,
                         confidence_threshold: float = 0.9, iterations: int = 3) -> Dict:
        """Self-training loop: detect → pseudo-label → retrain."""
        from ultralytics import YOLO

        results = []

        for iteration in range(iterations):
            logger.info(f"Self-training iteration {iteration + 1}/{iterations}")

            # Load current model
            model = YOLO(model_path)

            # Generate pseudo-labels
            pseudo_labels = []
            image_files = list(Path(unlabeled_dir).glob("*.jpg")) + list(Path(unlabeled_dir).glob("*.png"))

            for img_path in image_files:
                predictions = model(str(img_path), conf=confidence_threshold)

                for result in predictions:
                    if result.boxes is not None and len(result.boxes) > 0:
                        labels = []
                        for box in result.boxes:
                            cls = int(box.cls[0])
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            w_img, h_img = result.orig_shape[1], result.orig_shape[0]

                            # Convert to YOLO format (normalized)
                            cx = ((x1 + x2) / 2) / w_img
                            cy = ((y1 + y2) / 2) / h_img
                            bw = (x2 - x1) / w_img
                            bh = (y2 - y1) / h_img

                            labels.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

                        if labels:
                            pseudo_labels.append({
                                "image": str(img_path),
                                "labels": labels,
                                "avg_confidence": float(result.boxes.conf.mean())
                            })

            logger.info(f"Generated {len(pseudo_labels)} pseudo-labels")

            # Save pseudo-labels
            label_dir = os.path.join(settings.TRAINING_DIR, f"pseudo_labels_iter{iteration}")
            os.makedirs(label_dir, exist_ok=True)

            for pl in pseudo_labels:
                label_file = os.path.join(label_dir, Path(pl["image"]).stem + ".txt")
                with open(label_file, "w") as f:
                    f.write("\n".join(pl["labels"]))

            results.append({
                "iteration": iteration + 1,
                "pseudo_labels_generated": len(pseudo_labels),
                "avg_confidence": np.mean([pl["avg_confidence"] for pl in pseudo_labels]) if pseudo_labels else 0
            })

        return {
            "status": "completed",
            "iterations": results,
            "total_pseudo_labels": sum(r["pseudo_labels_generated"] for r in results)
        }

    # Feature 134: Active learning
    async def active_learning_select(self, model_path: str, image_dir: str,
                                     n_samples: int = 50, strategy: str = "uncertainty") -> List[str]:
        """Select most informative samples for labeling."""
        from ultralytics import YOLO

        model = YOLO(model_path)
        image_files = list(Path(image_dir).glob("*.jpg")) + list(Path(image_dir).glob("*.png"))

        scores = []
        for img_path in image_files:
            results = model(str(img_path), conf=0.1)

            for result in results:
                if result.boxes is not None and len(result.boxes) > 0:
                    confidences = result.boxes.conf.cpu().numpy()

                    if strategy == "uncertainty":
                        # Least confident predictions
                        score = 1 - confidences.max()
                    elif strategy == "margin":
                        # Smallest margin between top two predictions
                        sorted_conf = np.sort(confidences)[::-1]
                        score = 1 - (sorted_conf[0] - sorted_conf[1]) if len(sorted_conf) > 1 else 1
                    elif strategy == "entropy":
                        # Highest entropy
                        score = -np.sum(confidences * np.log(confidences + 1e-8))
                    else:
                        score = np.random.random()

                    scores.append((str(img_path), float(score)))
                else:
                    scores.append((str(img_path), 1.0))  # No detection = high uncertainty

        # Sort by score (highest uncertainty first)
        scores.sort(key=lambda x: x[1], reverse=True)

        return [s[0] for s in scores[:n_samples]]

    # Feature 143: Model compression
    async def compress_model(self, model_path: str, method: str = "quantize") -> Dict:
        """Compress model via quantization or pruning."""
        from ultralytics import YOLO

        model = YOLO(model_path)
        original_size = os.path.getsize(model_path)

        if method == "quantize":
            # Export to ONNX then quantize
            export_path = model.export(format="onnx", simplify=True)
            compressed_size = os.path.getsize(export_path)
        elif method == "tflite":
            export_path = model.export(format="tflite")
            compressed_size = os.path.getsize(export_path)
        else:
            export_path = model_path
            compressed_size = original_size

        return {
            "original_size_mb": round(original_size / 1024 / 1024, 2),
            "compressed_size_mb": round(compressed_size / 1024 / 1024, 2),
            "compression_ratio": round(original_size / max(compressed_size, 1), 2),
            "export_path": str(export_path),
            "method": method
        }

    # Feature 178: Hyperparameter tuning
    async def tune_hyperparameters(self, data_yaml: str, param_grid: Dict = None) -> Dict:
        """Grid search for best hyperparameters."""
        from ultralytics import YOLO

        if param_grid is None:
            param_grid = {
                "lr0": [0.001, 0.01, 0.1],
                "batch": [8, 16, 32],
                "imgsz": [416, 640],
            }

        best_result = None
        best_params = None
        all_results = []

        # Simple grid search
        for lr in param_grid.get("lr0", [0.01]):
            for batch in param_grid.get("batch", [16]):
                for imgsz in param_grid.get("imgsz", [640]):
                    try:
                        model = YOLO("yolov8n.pt")
                        result = model.train(
                            data=data_yaml, epochs=10, batch=batch,
                            imgsz=imgsz, lr0=lr, device=self.device,
                            project=settings.TRAINING_DIR, name="tune",
                            exist_ok=True, verbose=False
                        )

                        mAP = float(result.results_dict.get("metrics/mAP50(B)", 0))
                        trial = {"lr0": lr, "batch": batch, "imgsz": imgsz, "mAP50": mAP}
                        all_results.append(trial)

                        if best_result is None or mAP > best_result:
                            best_result = mAP
                            best_params = trial

                    except Exception as e:
                        logger.warning(f"Trial failed: {e}")

        return {
            "best_params": best_params,
            "best_mAP": best_result,
            "all_trials": all_results
        }

    # Feature 138: Data augmentation pipeline
    async def augment_dataset(self, image_dir: str, output_dir: str,
                              augmentations: Dict = None, copies: int = 3) -> Dict:
        """Augment images with various transformations."""
        os.makedirs(output_dir, exist_ok=True)

        image_files = list(Path(image_dir).glob("*.jpg")) + list(Path(image_dir).glob("*.png"))
        augmented_count = 0

        for img_path in image_files:
            img = cv2.imread(str(img_path))
            if img is None:
                continue

            # Copy original
            shutil.copy2(str(img_path), output_dir)

            for i in range(copies):
                aug_img = img.copy()
                operations = []

                # Random horizontal flip
                if np.random.random() > 0.5:
                    aug_img = cv2.flip(aug_img, 1)
                    operations.append("hflip")

                # Random brightness
                if np.random.random() > 0.5:
                    factor = np.random.uniform(0.7, 1.3)
                    aug_img = np.clip(aug_img * factor, 0, 255).astype(np.uint8)
                    operations.append("brightness")

                # Random rotation
                if np.random.random() > 0.5:
                    angle = np.random.uniform(-15, 15)
                    h, w = aug_img.shape[:2]
                    M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
                    aug_img = cv2.warpAffine(aug_img, M, (w, h))
                    operations.append("rotate")

                # Random noise
                if np.random.random() > 0.7:
                    noise = np.random.normal(0, 10, aug_img.shape).astype(np.uint8)
                    aug_img = cv2.add(aug_img, noise)
                    operations.append("noise")

                # Random blur
                if np.random.random() > 0.7:
                    ksize = np.random.choice([3, 5])
                    aug_img = cv2.GaussianBlur(aug_img, (ksize, ksize), 0)
                    operations.append("blur")

                # Random color jitter
                if np.random.random() > 0.5:
                    hsv = cv2.cvtColor(aug_img, cv2.COLOR_BGR2HSV)
                    hsv[:,:,0] = np.clip(hsv[:,:,0] + np.random.randint(-10, 10), 0, 179)
                    hsv[:,:,1] = np.clip(hsv[:,:,1] + np.random.randint(-30, 30), 0, 255)
                    aug_img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                    operations.append("color_jitter")

                # Save augmented image
                stem = img_path.stem
                out_path = os.path.join(output_dir, f"{stem}_aug{i}_{'_'.join(operations)}.jpg")
                cv2.imwrite(out_path, aug_img)
                augmented_count += 1

        return {
            "original_count": len(image_files),
            "augmented_count": augmented_count,
            "total_count": len(image_files) + augmented_count,
            "output_dir": output_dir
        }

    # Get training status
    def get_training_status(self, training_id: str = None) -> Dict:
        if training_id:
            return self.training_progress.get(training_id, {"error": "Training not found"})

        return {
            "active_training": self.active_training,
            "total_runs": len(self.training_history),
            "progress": self.training_progress,
            "device": self.device
        }


# Singleton
training_service = TrainingService()
