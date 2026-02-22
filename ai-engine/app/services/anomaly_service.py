"""
Vision-AI Anomaly Detection Service
Features 1-5: Anomaly detection, pattern recognition, outlier scoring, trend deviation, baseline learning
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
from loguru import logger


class AnomalyDetector:
    """Statistical anomaly detection for sensor data and detections."""

    def __init__(self):
        self.baselines: Dict[str, dict] = {}
        self.data_windows: Dict[str, deque] = {}
        self.anomaly_history: List[dict] = []
        self.window_size = 1000
        self.z_threshold = 3.0
        self.iqr_multiplier = 1.5
        logger.info("Anomaly Detection Service initialized")

    # Feature 1: Z-Score Anomaly Detection
    def detect_zscore(self, metric_name: str, value: float) -> dict:
        """Detect anomalies using Z-score method."""
        if metric_name not in self.data_windows:
            self.data_windows[metric_name] = deque(maxlen=self.window_size)
        
        self.data_windows[metric_name].append(value)
        window = list(self.data_windows[metric_name])
        
        if len(window) < 10:
            return {"is_anomaly": False, "score": 0, "method": "zscore"}
        
        mean = np.mean(window)
        std = np.std(window)
        if std == 0:
            return {"is_anomaly": False, "score": 0, "method": "zscore"}
        
        z_score = abs((value - mean) / std)
        is_anomaly = z_score > self.z_threshold
        
        result = {
            "is_anomaly": is_anomaly,
            "score": float(z_score),
            "threshold": self.z_threshold,
            "mean": float(mean),
            "std": float(std),
            "value": value,
            "method": "zscore",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if is_anomaly:
            self.anomaly_history.append(result)
            logger.warning(f"Anomaly detected in {metric_name}: z={z_score:.2f}")
        
        return result

    # Feature 2: IQR-Based Outlier Detection
    def detect_iqr(self, metric_name: str, values: List[float]) -> dict:
        """Detect outliers using Interquartile Range method."""
        if len(values) < 4:
            return {"outliers": [], "method": "iqr"}
        
        arr = np.array(values)
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1
        lower = q1 - self.iqr_multiplier * iqr
        upper = q3 + self.iqr_multiplier * iqr
        
        outliers = [
            {"index": i, "value": float(v), "type": "high" if v > upper else "low"}
            for i, v in enumerate(values)
            if v < lower or v > upper
        ]
        
        return {
            "outliers": outliers,
            "bounds": {"lower": float(lower), "upper": float(upper)},
            "q1": float(q1), "q3": float(q3), "iqr": float(iqr),
            "total_points": len(values),
            "outlier_count": len(outliers),
            "method": "iqr"
        }

    # Feature 3: Moving Average Deviation Detection
    def detect_moving_average(self, metric_name: str, value: float, window: int = 50) -> dict:
        """Detect deviations from moving average."""
        if metric_name not in self.data_windows:
            self.data_windows[metric_name] = deque(maxlen=self.window_size)
        
        self.data_windows[metric_name].append(value)
        data = list(self.data_windows[metric_name])
        
        if len(data) < window:
            return {"is_anomaly": False, "deviation": 0, "method": "moving_average"}
        
        recent = data[-window:]
        ma = np.mean(recent)
        deviation = abs(value - ma) / (ma if ma != 0 else 1)
        is_anomaly = deviation > 0.3  # 30% deviation threshold
        
        return {
            "is_anomaly": is_anomaly,
            "deviation": float(deviation),
            "moving_average": float(ma),
            "value": value,
            "window_size": window,
            "method": "moving_average"
        }

    # Feature 4: Baseline Learning
    def learn_baseline(self, metric_name: str, values: List[float]) -> dict:
        """Learn normal baseline patterns from historical data."""
        arr = np.array(values)
        self.baselines[metric_name] = {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "median": float(np.median(arr)),
            "p5": float(np.percentile(arr, 5)),
            "p95": float(np.percentile(arr, 95)),
            "samples": len(values),
            "learned_at": datetime.utcnow().isoformat()
        }
        logger.info(f"Baseline learned for {metric_name}: mean={self.baselines[metric_name]['mean']:.2f}")
        return self.baselines[metric_name]

    # Feature 5: Multi-Metric Correlation Anomaly
    def detect_correlation_anomaly(self, metrics: Dict[str, float]) -> dict:
        """Detect anomalies based on metric correlations breaking."""
        anomalies = []
        for name, value in metrics.items():
            if name in self.baselines:
                bl = self.baselines[name]
                if value < bl["p5"] or value > bl["p95"]:
                    anomalies.append({
                        "metric": name,
                        "value": value,
                        "expected_range": [bl["p5"], bl["p95"]],
                        "severity": "high" if (value < bl["min"] or value > bl["max"]) else "medium"
                    })
        
        return {
            "has_anomalies": len(anomalies) > 0,
            "anomalies": anomalies,
            "metrics_checked": len(metrics),
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_history(self, limit: int = 100) -> List[dict]:
        return self.anomaly_history[-limit:]

    def get_baselines(self) -> Dict[str, dict]:
        return self.baselines


anomaly_detector = AnomalyDetector()
