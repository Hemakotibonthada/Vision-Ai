"""
Vision-AI Analytics Service
Features: Metrics, statistics, trends, reporting
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter

import numpy as np
from loguru import logger
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Detection, Event, SensorData, Device


class AnalyticsService:
    """Comprehensive analytics and reporting service."""

    # Feature 263: Object count over time
    async def get_detection_timeline(self, db: AsyncSession, hours: int = 24,
                                     interval_minutes: int = 60) -> List[Dict]:
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(Detection).where(Detection.created_at >= since).order_by(Detection.created_at)
        )
        detections = result.scalars().all()

        timeline = defaultdict(lambda: {"total": 0, "classes": defaultdict(int)})
        for det in detections:
            bucket = det.created_at.replace(
                minute=(det.created_at.minute // interval_minutes) * interval_minutes,
                second=0, microsecond=0
            )
            bucket_key = bucket.isoformat()
            timeline[bucket_key]["total"] += det.total_objects
            if det.classes_detected:
                for cls in det.classes_detected:
                    counts = det.results if isinstance(det.results, list) else []
                    class_count = sum(1 for r in counts if r.get("class") == cls)
                    timeline[bucket_key]["classes"][cls] += class_count

        return [
            {"timestamp": k, "total": v["total"], "classes": dict(v["classes"])}
            for k, v in sorted(timeline.items())
        ]

    # Feature 264: Peak hours analysis
    async def get_peak_hours(self, db: AsyncSession, days: int = 7) -> Dict:
        since = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(Detection).where(Detection.created_at >= since)
        )
        detections = result.scalars().all()

        hourly_counts = defaultdict(int)
        for det in detections:
            hour = det.created_at.hour
            hourly_counts[hour] += det.total_objects

        peak_hour = max(hourly_counts, key=hourly_counts.get) if hourly_counts else 0

        return {
            "hourly_distribution": dict(sorted(hourly_counts.items())),
            "peak_hour": peak_hour,
            "peak_count": hourly_counts.get(peak_hour, 0),
            "total_detections": sum(hourly_counts.values()),
            "period_days": days
        }

    # Feature 265: Daily/weekly/monthly trends
    async def get_trends(self, db: AsyncSession, period: str = "daily", days: int = 30) -> List[Dict]:
        since = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(Detection).where(Detection.created_at >= since).order_by(Detection.created_at)
        )
        detections = result.scalars().all()

        trends = defaultdict(lambda: {"count": 0, "total_objects": 0, "avg_confidence": [], "classes": defaultdict(int)})

        for det in detections:
            if period == "daily":
                key = det.created_at.strftime("%Y-%m-%d")
            elif period == "weekly":
                key = det.created_at.strftime("%Y-W%W")
            elif period == "monthly":
                key = det.created_at.strftime("%Y-%m")
            else:
                key = det.created_at.strftime("%Y-%m-%d %H:00")

            trends[key]["count"] += 1
            trends[key]["total_objects"] += det.total_objects
            if det.confidence_avg:
                trends[key]["avg_confidence"].append(det.confidence_avg)
            if det.classes_detected:
                for cls in det.classes_detected:
                    trends[key]["classes"][cls] += 1

        result = []
        for k, v in sorted(trends.items()):
            avg_conf = np.mean(v["avg_confidence"]) if v["avg_confidence"] else 0
            result.append({
                "period": k,
                "detections": v["count"],
                "total_objects": v["total_objects"],
                "avg_confidence": round(float(avg_conf), 4),
                "top_classes": dict(Counter(v["classes"]).most_common(5))
            })

        return result

    # Feature 266: Comparative analytics
    async def compare_periods(self, db: AsyncSession,
                              period1_start: datetime, period1_end: datetime,
                              period2_start: datetime, period2_end: datetime) -> Dict:
        async def get_period_stats(start, end):
            result = await db.execute(
                select(Detection).where(
                    and_(Detection.created_at >= start, Detection.created_at <= end)
                )
            )
            dets = result.scalars().all()
            
            total_objects = sum(d.total_objects for d in dets)
            avg_conf = np.mean([d.confidence_avg for d in dets if d.confidence_avg]) if dets else 0
            avg_time = np.mean([d.inference_time_ms for d in dets if d.inference_time_ms]) if dets else 0
            
            class_dist = defaultdict(int)
            for d in dets:
                if d.classes_detected:
                    for cls in d.classes_detected:
                        class_dist[cls] += 1

            return {
                "total_detections": len(dets),
                "total_objects": total_objects,
                "avg_confidence": round(float(avg_conf), 4),
                "avg_inference_ms": round(float(avg_time), 2),
                "class_distribution": dict(class_dist)
            }

        period1_stats = await get_period_stats(period1_start, period1_end)
        period2_stats = await get_period_stats(period2_start, period2_end)

        # Calculate changes
        def calc_change(v1, v2):
            if v1 == 0: return 100.0 if v2 > 0 else 0.0
            return round((v2 - v1) / v1 * 100, 2)

        return {
            "period1": period1_stats,
            "period2": period2_stats,
            "changes": {
                "detections_change_pct": calc_change(period1_stats["total_detections"], period2_stats["total_detections"]),
                "objects_change_pct": calc_change(period1_stats["total_objects"], period2_stats["total_objects"]),
                "confidence_change_pct": calc_change(period1_stats["avg_confidence"], period2_stats["avg_confidence"])
            }
        }

    # Feature 269: Zone occupancy (virtual zones)
    async def get_zone_analytics(self, db: AsyncSession, zone_id: int, hours: int = 24) -> Dict:
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(Detection).where(Detection.created_at >= since)
        )
        detections = result.scalars().all()

        # This would be enhanced with actual zone polygon checking
        occupancy_timeline = []
        for det in detections:
            if det.results:
                in_zone = len(det.results)  # Simplified
                occupancy_timeline.append({
                    "timestamp": det.created_at.isoformat(),
                    "count": in_zone,
                })

        return {
            "zone_id": zone_id,
            "avg_occupancy": np.mean([o["count"] for o in occupancy_timeline]) if occupancy_timeline else 0,
            "max_occupancy": max([o["count"] for o in occupancy_timeline]) if occupancy_timeline else 0,
            "timeline": occupancy_timeline[-100:]  # Last 100 entries
        }

    # Feature 170: Confusion matrix generation
    async def generate_confusion_matrix(self, predictions: List[Dict], ground_truth: List[Dict]) -> Dict:
        classes = sorted(set(
            [p.get("predicted", "") for p in predictions] +
            [g.get("actual", "") for g in ground_truth]
        ))

        n_classes = len(classes)
        matrix = np.zeros((n_classes, n_classes), dtype=int)

        class_to_idx = {c: i for i, c in enumerate(classes)}

        for pred, gt in zip(predictions, ground_truth):
            pred_idx = class_to_idx.get(pred.get("predicted", ""), 0)
            gt_idx = class_to_idx.get(gt.get("actual", ""), 0)
            matrix[gt_idx][pred_idx] += 1

        # Calculate metrics per class
        per_class = {}
        for i, cls in enumerate(classes):
            tp = matrix[i][i]
            fp = matrix[:, i].sum() - tp
            fn = matrix[i, :].sum() - tp
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            per_class[cls] = {
                "true_positives": int(tp), "false_positives": int(fp),
                "false_negatives": int(fn), "precision": round(precision, 4),
                "recall": round(recall, 4), "f1_score": round(f1, 4)
            }

        total_correct = np.trace(matrix)
        total = matrix.sum()

        return {
            "matrix": matrix.tolist(),
            "classes": classes,
            "per_class_metrics": per_class,
            "overall_accuracy": round(total_correct / total, 4) if total > 0 else 0,
            "total_samples": int(total)
        }

    # Feature 171: Precision-Recall curves
    async def precision_recall_curve(self, detections: List[Dict], thresholds: List[float] = None) -> Dict:
        if thresholds is None:
            thresholds = [i / 20 for i in range(1, 20)]

        curves = {}
        for det in detections:
            for d in det.get("detections", []):
                cls = d.get("class", "unknown")
                if cls not in curves:
                    curves[cls] = []
                curves[cls].append(d.get("confidence", 0))

        result = {}
        for cls, confidences in curves.items():
            points = []
            for threshold in thresholds:
                tp = sum(1 for c in confidences if c >= threshold)
                total = len(confidences)
                precision = tp / total if total > 0 else 0
                recall = tp / (tp + 1) if (tp + 1) > 0 else 0  # Simplified

                points.append({
                    "threshold": threshold,
                    "precision": round(precision, 4),
                    "recall": round(recall, 4)
                })

            result[cls] = points

        return {"classes": result, "thresholds": thresholds}

    # Feature 161: Dataset statistics
    async def get_dataset_stats(self, db: AsyncSession, dataset_id: int) -> Dict:
        from app.database import DatasetImage
        result = await db.execute(
            select(DatasetImage).where(DatasetImage.dataset_id == dataset_id)
        )
        images = result.scalars().all()

        class_counts = defaultdict(int)
        sizes = []
        splits = defaultdict(int)

        for img in images:
            if img.labels:
                for label in img.labels:
                    class_counts[label] += 1
            if img.file_size:
                sizes.append(img.file_size)
            splits[img.split or "unassigned"] += 1

        return {
            "total_images": len(images),
            "class_distribution": dict(class_counts),
            "split_distribution": dict(splits),
            "avg_file_size": np.mean(sizes) if sizes else 0,
            "total_size_mb": sum(sizes) / 1024 / 1024 if sizes else 0,
            "num_classes": len(class_counts),
            "most_common_class": max(class_counts, key=class_counts.get) if class_counts else None,
            "least_common_class": min(class_counts, key=class_counts.get) if class_counts else None,
            "class_balance_ratio": min(class_counts.values()) / max(class_counts.values()) if len(class_counts) > 1 else 1.0
        }

    # Feature 271: Report generation
    async def generate_report(self, db: AsyncSession, report_type: str = "daily",
                              start_date: datetime = None, end_date: datetime = None) -> Dict:
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=1 if report_type == "daily" else 7)

        # Gather all data
        det_result = await db.execute(
            select(Detection).where(
                and_(Detection.created_at >= start_date, Detection.created_at <= end_date)
            )
        )
        detections = det_result.scalars().all()

        event_result = await db.execute(
            select(Event).where(
                and_(Event.created_at >= start_date, Event.created_at <= end_date)
            )
        )
        events = event_result.scalars().all()

        # Compile report
        total_objects = sum(d.total_objects for d in detections)
        class_dist = defaultdict(int)
        for d in detections:
            if d.classes_detected:
                for cls in d.classes_detected:
                    class_dist[cls] += 1

        event_types = defaultdict(int)
        for e in events:
            event_types[e.event_type] += 1

        return {
            "report_type": report_type,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_detections": len(detections),
                "total_objects_detected": total_objects,
                "unique_classes": len(class_dist),
                "total_events": len(events),
                "avg_inference_ms": round(np.mean([d.inference_time_ms for d in detections if d.inference_time_ms]) if detections else 0, 2),
                "avg_confidence": round(np.mean([d.confidence_avg for d in detections if d.confidence_avg]) if detections else 0, 4)
            },
            "class_distribution": dict(class_dist),
            "event_distribution": dict(event_types),
            "generated_at": datetime.utcnow().isoformat()
        }

    # Feature: Dashboard summary
    async def get_dashboard_summary(self, db: AsyncSession) -> Dict:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Today's detections
        det_result = await db.execute(
            select(func.count(Detection.id)).where(Detection.created_at >= today_start)
        )
        today_detections = det_result.scalar() or 0

        # Active devices
        dev_result = await db.execute(
            select(func.count(Device.id)).where(Device.status == "online")
        )
        active_devices = dev_result.scalar() or 0

        # Today's events
        event_result = await db.execute(
            select(func.count(Event.id)).where(Event.created_at >= today_start)
        )
        today_events = event_result.scalar() or 0

        # Total models
        from app.database import AIModel
        model_result = await db.execute(select(func.count(AIModel.id)))
        total_models = model_result.scalar() or 0

        # Recent detections for chart
        recent = await self.get_detection_timeline(db, hours=24, interval_minutes=60)

        return {
            "today_detections": today_detections,
            "active_devices": active_devices,
            "today_events": today_events,
            "total_models": total_models,
            "hourly_chart": recent[-24:],
            "timestamp": now.isoformat()
        }


# Singleton
analytics_service = AnalyticsService()
