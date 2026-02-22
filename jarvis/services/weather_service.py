"""
Jarvis Weather Integration Service
Feature 26: Weather data integration and analysis
Feature 27: Weather-based automation
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger


class WeatherService:
    """Weather integration and weather-based automation."""

    def __init__(self):
        self.current_weather = {
            "temperature": 22.0,
            "humidity": 55,
            "condition": "clear",
            "wind_speed": 10,
            "pressure": 1013,
            "visibility": 10,
            "uv_index": 3,
            "forecast": "sunny",
            "updated_at": datetime.utcnow().isoformat()
        }
        self.weather_history = []
        self.weather_rules = []
        self.alerts = []
        logger.info("Weather Service initialized")

    def update_weather(self, data: dict):
        """Update current weather data (from API or sensor)."""
        self.current_weather.update(data)
        self.current_weather["updated_at"] = datetime.utcnow().isoformat()
        self.weather_history.append({**self.current_weather})
        if len(self.weather_history) > 1000:
            self.weather_history = self.weather_history[-500:]
        self._evaluate_rules()

    def get_current(self) -> dict:
        return self.current_weather

    def get_forecast_summary(self) -> dict:
        """Generate forecast based on trends."""
        if len(self.weather_history) < 5:
            return {"forecast": self.current_weather.get("forecast", "unknown"), "confidence": 0.3}
        
        recent_temps = [w.get("temperature", 0) for w in self.weather_history[-10:]]
        trend = "rising" if recent_temps[-1] > recent_temps[0] else "falling" if recent_temps[-1] < recent_temps[0] else "stable"
        
        return {
            "current": self.current_weather,
            "trend": trend,
            "temp_trend": round(recent_temps[-1] - recent_temps[0], 1),
            "avg_temp": round(sum(recent_temps) / len(recent_temps), 1),
            "confidence": 0.6,
            "recommendation": self._get_recommendation()
        }

    def _get_recommendation(self) -> str:
        temp = self.current_weather.get("temperature", 22)
        humidity = self.current_weather.get("humidity", 50)
        if temp > 35: return "Very hot - ensure cooling is active"
        if temp < 5: return "Very cold - ensure heating is active"
        if humidity > 80: return "High humidity - consider dehumidifier"
        if humidity < 30: return "Low humidity - consider humidifier"
        return "Comfortable conditions"

    def add_weather_rule(self, rule: dict):
        """Feature 27: Add weather-based automation rule."""
        self.weather_rules.append({
            "id": len(self.weather_rules) + 1,
            "condition": rule.get("condition"),
            "threshold": rule.get("threshold"),
            "action": rule.get("action"),
            "enabled": True,
            "created_at": datetime.utcnow().isoformat()
        })

    def _evaluate_rules(self):
        for rule in self.weather_rules:
            if not rule.get("enabled"):
                continue
            field = rule["condition"].get("field", "temperature")
            op = rule["condition"].get("op", ">")
            threshold = rule["condition"].get("value", 30)
            current = self.current_weather.get(field, 0)
            
            triggered = False
            if op == ">" and current > threshold: triggered = True
            elif op == "<" and current < threshold: triggered = True
            elif op == "==" and current == threshold: triggered = True
            
            if triggered:
                self.alerts.append({
                    "rule_id": rule["id"],
                    "action": rule["action"],
                    "triggered_at": datetime.utcnow().isoformat(),
                    "value": current
                })

    def get_alerts(self) -> List[dict]:
        return self.alerts[-50:]

    def get_history(self, limit: int = 100) -> List[dict]:
        return self.weather_history[-limit:]


weather_service = WeatherService()
