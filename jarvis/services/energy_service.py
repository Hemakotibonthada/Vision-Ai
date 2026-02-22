"""
Jarvis Energy Monitoring Service
Feature 28: Power consumption tracking
Feature 29: Energy optimization recommendations
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from loguru import logger


class EnergyMonitorService:
    """Track and optimize energy consumption across devices."""

    def __init__(self):
        self.device_power = {}  # device_id -> watts
        self.consumption_log = []
        self.tariff_schedule = {
            "peak": {"start": 17, "end": 21, "rate": 0.25},
            "off_peak": {"start": 23, "end": 7, "rate": 0.10},
            "standard": {"rate": 0.15}
        }
        self.daily_budget_kwh = 50.0
        self.monthly_target_kwh = 1500.0
        self.energy_alerts = []
        logger.info("Energy Monitor Service initialized")

    def update_power(self, device_id: str, watts: float, voltage: float = 220, current: float = 0):
        """Update real-time power reading from a device."""
        self.device_power[device_id] = {
            "watts": watts,
            "voltage": voltage,
            "current": current if current else watts / voltage,
            "updated_at": datetime.utcnow().isoformat()
        }
        self.consumption_log.append({
            "device_id": device_id,
            "watts": watts,
            "timestamp": datetime.utcnow().isoformat()
        })
        if len(self.consumption_log) > 10000:
            self.consumption_log = self.consumption_log[-5000:]

    def get_current_usage(self) -> dict:
        """Get current power consumption summary."""
        total_watts = sum(d["watts"] for d in self.device_power.values())
        return {
            "total_watts": round(total_watts, 1),
            "total_kw": round(total_watts / 1000, 3),
            "devices": self.device_power,
            "device_count": len(self.device_power),
            "estimated_daily_kwh": round(total_watts * 24 / 1000, 2),
            "current_rate": self._get_current_rate(),
            "estimated_daily_cost": round(total_watts * 24 / 1000 * self._get_current_rate()["rate"], 2),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _get_current_rate(self) -> dict:
        hour = datetime.utcnow().hour
        peak = self.tariff_schedule["peak"]
        off_peak = self.tariff_schedule["off_peak"]
        if peak["start"] <= hour < peak["end"]:
            return {"period": "peak", "rate": peak["rate"]}
        if hour >= off_peak["start"] or hour < off_peak["end"]:
            return {"period": "off_peak", "rate": off_peak["rate"]}
        return {"period": "standard", "rate": self.tariff_schedule["standard"]["rate"]}

    def get_daily_summary(self) -> dict:
        """Get today's energy consumption summary."""
        today = datetime.utcnow().date().isoformat()
        today_logs = [l for l in self.consumption_log if l["timestamp"].startswith(today)]
        
        by_device = defaultdict(list)
        for log in today_logs:
            by_device[log["device_id"]].append(log["watts"])
        
        device_summary = {}
        for did, watts_list in by_device.items():
            avg_watts = sum(watts_list) / len(watts_list)
            device_summary[did] = {
                "avg_watts": round(avg_watts, 1),
                "readings": len(watts_list),
                "estimated_kwh": round(avg_watts * 24 / 1000, 2)
            }
        
        total_estimated = sum(d["estimated_kwh"] for d in device_summary.values())
        return {
            "date": today,
            "total_kwh": round(total_estimated, 2),
            "budget_kwh": self.daily_budget_kwh,
            "budget_remaining": round(self.daily_budget_kwh - total_estimated, 2),
            "within_budget": total_estimated <= self.daily_budget_kwh,
            "devices": device_summary,
            "readings": len(today_logs)
        }

    def get_optimization_tips(self) -> List[dict]:
        """Feature 29: Generate energy optimization recommendations."""
        tips = []
        usage = self.get_current_usage()
        
        if usage["total_watts"] > 3000:
            tips.append({"priority": "high", "tip": "High total consumption detected. Consider turning off non-essential devices.", "potential_saving": "20-30%"})
        
        rate = self._get_current_rate()
        if rate["period"] == "peak":
            tips.append({"priority": "high", "tip": "Currently in peak tariff period. Defer heavy loads to off-peak hours.", "potential_saving": "40%"})
        
        for did, info in self.device_power.items():
            if info["watts"] > 1000:
                tips.append({"priority": "medium", "tip": f"Device {did} consuming {info['watts']}W. Check if needed.", "device": did})
            if info["watts"] < 5 and info["watts"] > 0:
                tips.append({"priority": "low", "tip": f"Device {did} in standby ({info['watts']}W). Consider full shutdown.", "device": did})
        
        tips.append({"priority": "info", "tip": "Schedule heavy appliances during off-peak hours (11PM-7AM) for lower rates."})
        return tips

    def set_budget(self, daily_kwh: float = None, monthly_kwh: float = None):
        if daily_kwh: self.daily_budget_kwh = daily_kwh
        if monthly_kwh: self.monthly_target_kwh = monthly_kwh

    def get_stats(self) -> dict:
        return {
            "total_readings": len(self.consumption_log),
            "active_devices": len(self.device_power),
            "daily_budget": self.daily_budget_kwh,
            "monthly_target": self.monthly_target_kwh
        }


energy_service = EnergyMonitorService()
