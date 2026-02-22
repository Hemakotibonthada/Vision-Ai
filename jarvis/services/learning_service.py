"""
Jarvis AI - Learning Service
===============================
Tracks owner patterns, habits, and preferences over time.
Adapts Jarvis behavior based on learned data.
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter, defaultdict

from loguru import logger

from jarvis.config import settings


class LearningService:
    """Learns and adapts from owner behavior patterns."""

    def __init__(self):
        self._data_file = os.path.join(settings.LEARNING_DIR, "learning_data.json")
        self._data: Dict = self._load_data()
        logger.info("Learning service initialized")

    # ================================================================
    # Persistence
    # ================================================================
    def _load_data(self) -> Dict:
        """Load learning data from disk."""
        if os.path.exists(self._data_file):
            try:
                with open(self._data_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load learning data: {e}")

        return {
            "arrival_times": [],       # When owner typically arrives
            "departure_times": [],     # When owner typically leaves
            "command_frequency": {},   # Most used commands
            "room_preferences": {},    # Preferred devices/scenes by time
            "daily_patterns": {},      # Day-of-week patterns
            "interaction_count": 0,
            "last_learning_cycle": None,
            "created_at": datetime.now().isoformat(),
        }

    def _save_data(self):
        """Persist learning data to disk."""
        try:
            os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
            with open(self._data_file, "w") as f:
                json.dump(self._data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")

    # ================================================================
    # Record Events
    # ================================================================
    def record_arrival(self):
        """Record when the owner arrives."""
        now = datetime.now()
        entry = {
            "time": now.strftime("%H:%M"),
            "day": now.strftime("%A"),
            "date": now.strftime("%Y-%m-%d"),
        }
        self._data["arrival_times"].append(entry)
        # Keep last 100 entries
        self._data["arrival_times"] = self._data["arrival_times"][-100:]
        self._save_data()

    def record_departure(self):
        """Record when the owner departs."""
        now = datetime.now()
        entry = {
            "time": now.strftime("%H:%M"),
            "day": now.strftime("%A"),
            "date": now.strftime("%Y-%m-%d"),
        }
        self._data["departure_times"].append(entry)
        self._data["departure_times"] = self._data["departure_times"][-100:]
        self._save_data()

    def record_command(self, command: str):
        """Record a command for frequency analysis."""
        cmd = command.lower().strip()
        self._data["command_frequency"][cmd] = self._data["command_frequency"].get(cmd, 0) + 1
        self._data["interaction_count"] += 1
        self._save_data()

    def record_room_preference(self, action: str, time_of_day: str):
        """Record a room/device preference at a specific time."""
        key = time_of_day  # morning, afternoon, evening, night
        if key not in self._data["room_preferences"]:
            self._data["room_preferences"][key] = {}
        prefs = self._data["room_preferences"][key]
        prefs[action] = prefs.get(action, 0) + 1
        self._save_data()

    # ================================================================
    # Analysis & Predictions
    # ================================================================
    def get_typical_arrival_time(self) -> Optional[str]:
        """Predict typical arrival time based on history."""
        times = self._data.get("arrival_times", [])
        if len(times) < 5:
            return None

        # Get most common hour
        hours = []
        for t in times:
            try:
                h = int(t["time"].split(":")[0])
                hours.append(h)
            except (ValueError, KeyError):
                pass

        if not hours:
            return None

        most_common = Counter(hours).most_common(1)[0][0]
        return f"{most_common:02d}:00"

    def get_typical_departure_time(self) -> Optional[str]:
        """Predict typical departure time."""
        times = self._data.get("departure_times", [])
        if len(times) < 5:
            return None

        hours = []
        for t in times:
            try:
                h = int(t["time"].split(":")[0])
                hours.append(h)
            except (ValueError, KeyError):
                pass

        if not hours:
            return None

        most_common = Counter(hours).most_common(1)[0][0]
        return f"{most_common:02d}:00"

    def get_top_commands(self, n: int = 5) -> List[tuple]:
        """Get most frequently used commands."""
        freq = self._data.get("command_frequency", {})
        return Counter(freq).most_common(n)

    def get_time_of_day(self) -> str:
        """Get current time of day category."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def suggest_actions(self) -> List[str]:
        """Suggest actions based on current time and learned patterns."""
        tod = self.get_time_of_day()
        prefs = self._data.get("room_preferences", {}).get(tod, {})

        if not prefs:
            return []

        sorted_prefs = sorted(prefs.items(), key=lambda x: x[1], reverse=True)
        return [action for action, _ in sorted_prefs[:3]]

    def get_summary(self) -> Dict:
        """Get a summary of learned data."""
        return {
            "total_interactions": self._data.get("interaction_count", 0),
            "typical_arrival": self.get_typical_arrival_time(),
            "typical_departure": self.get_typical_departure_time(),
            "top_commands": self.get_top_commands(),
            "time_of_day": self.get_time_of_day(),
            "suggested_actions": self.suggest_actions(),
            "data_points": {
                "arrivals": len(self._data.get("arrival_times", [])),
                "departures": len(self._data.get("departure_times", [])),
                "commands": len(self._data.get("command_frequency", {})),
            },
        }

    def run_learning_cycle(self):
        """Run a learning analysis cycle."""
        self._data["last_learning_cycle"] = datetime.now().isoformat()
        self._save_data()
        logger.info("Learning cycle completed")
        return self.get_summary()


# Singleton
learning_service = LearningService()
