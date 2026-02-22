"""
Jarvis Advanced Intelligence Services
Features 30-45: Scene memory, predictive automation, calendar, guest management,
sleep monitoring, NLU, conversation context, habit learning, emergency protocols,
geofencing, device health, timelapse, notification priority, scene analyzer,
backup/restore, task scheduler
"""
import json
import time
import math
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, Counter
from loguru import logger


class SceneMemoryService:
    """Feature 30: Remember room states and detect changes."""

    def __init__(self):
        self.room_states = {}
        self.change_log = []
        logger.info("Scene Memory Service initialized")

    def save_scene(self, room: str, state: dict):
        """Save current room state snapshot."""
        self.room_states[room] = {
            "state": state,
            "saved_at": datetime.utcnow().isoformat(),
            "hash": hashlib.md5(json.dumps(state, sort_keys=True).encode()).hexdigest()
        }

    def detect_changes(self, room: str, current_state: dict) -> dict:
        """Compare current state to saved scene."""
        if room not in self.room_states:
            return {"changed": False, "message": "No baseline scene saved"}
        
        saved = self.room_states[room]["state"]
        changes = []
        for key, val in current_state.items():
            if key in saved and saved[key] != val:
                changes.append({"field": key, "was": saved[key], "now": val})
        for key in saved:
            if key not in current_state:
                changes.append({"field": key, "was": saved[key], "now": None})
        
        if changes:
            self.change_log.append({"room": room, "changes": changes, "timestamp": datetime.utcnow().isoformat()})
        
        return {"changed": len(changes) > 0, "changes": changes, "change_count": len(changes)}

    def get_room_state(self, room: str) -> dict:
        return self.room_states.get(room, {})

    def get_change_log(self, limit: int = 50) -> List[dict]:
        return self.change_log[-limit:]


class PredictiveAutomationService:
    """Feature 31: Predict user behavior and automate proactively."""

    def __init__(self):
        self.behavior_log = []
        self.patterns = {}
        self.predictions = []
        logger.info("Predictive Automation Service initialized")

    def log_behavior(self, action: str, context: dict = None):
        """Log a user behavior for pattern learning."""
        entry = {
            "action": action,
            "context": context or {},
            "hour": datetime.utcnow().hour,
            "day_of_week": datetime.utcnow().weekday(),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.behavior_log.append(entry)
        if len(self.behavior_log) > 5000:
            self.behavior_log = self.behavior_log[-2500:]

    def learn_patterns(self) -> dict:
        """Analyze behavior logs to discover patterns."""
        hourly = defaultdict(lambda: defaultdict(int))
        daily = defaultdict(lambda: defaultdict(int))
        sequences = []
        
        for entry in self.behavior_log:
            hourly[entry["hour"]][entry["action"]] += 1
            daily[entry["day_of_week"]][entry["action"]] += 1
        
        # Find most common action per hour
        patterns = {}
        for hour, actions in hourly.items():
            top_action = max(actions, key=actions.get)
            patterns[f"hour_{hour}"] = {
                "action": top_action,
                "count": actions[top_action],
                "confidence": round(actions[top_action] / sum(actions.values()), 3)
            }
        
        self.patterns = patterns
        return {"patterns_discovered": len(patterns), "patterns": patterns}

    def predict_next_action(self) -> dict:
        """Predict what the user will do next based on patterns."""
        current_hour = datetime.utcnow().hour
        key = f"hour_{current_hour}"
        if key in self.patterns:
            pattern = self.patterns[key]
            return {
                "predicted_action": pattern["action"],
                "confidence": pattern["confidence"],
                "based_on": f"{pattern['count']} historical occurrences at hour {current_hour}"
            }
        return {"predicted_action": None, "confidence": 0, "message": "Insufficient data"}

    def get_suggestions(self) -> List[dict]:
        """Get proactive automation suggestions."""
        predictions = []
        pred = self.predict_next_action()
        if pred["predicted_action"]:
            predictions.append({
                "suggestion": f"Based on your patterns, you usually '{pred['predicted_action']}' at this time.",
                "action": pred["predicted_action"],
                "auto_execute": pred["confidence"] > 0.8
            })
        return predictions


class CalendarService:
    """Feature 32: Schedule-aware automation."""

    def __init__(self):
        self.events = []
        self.recurring = []
        logger.info("Calendar Service initialized")

    def add_event(self, title: str, start: str, end: str = None, 
                  recurring: str = None, actions: list = None) -> dict:
        event = {
            "id": len(self.events) + 1,
            "title": title,
            "start": start,
            "end": end,
            "recurring": recurring,  # daily, weekly, monthly
            "actions": actions or [],
            "created_at": datetime.utcnow().isoformat()
        }
        self.events.append(event)
        return event

    def get_upcoming(self, hours: int = 24) -> List[dict]:
        """Get events in the next N hours."""
        now = datetime.utcnow()
        upcoming = []
        for event in self.events:
            try:
                start = datetime.fromisoformat(event["start"])
                if now <= start <= now + timedelta(hours=hours):
                    upcoming.append(event)
            except (ValueError, TypeError):
                pass
        return sorted(upcoming, key=lambda e: e["start"])

    def get_today(self) -> List[dict]:
        return self.get_upcoming(24)

    def delete_event(self, event_id: int) -> bool:
        self.events = [e for e in self.events if e.get("id") != event_id]
        return True

    def get_all(self) -> List[dict]:
        return self.events


class GuestManagementService:
    """Feature 33: Track and manage visitors."""

    def __init__(self):
        self.guests = {}
        self.visit_log = []
        self.access_rules = {}
        logger.info("Guest Management Service initialized")

    def register_guest(self, name: str, face_id: str = None, 
                       access_level: str = "visitor") -> dict:
        guest_id = f"guest_{len(self.guests) + 1}"
        self.guests[guest_id] = {
            "name": name,
            "face_id": face_id,
            "access_level": access_level,  # visitor, trusted, vip, blocked
            "registered_at": datetime.utcnow().isoformat(),
            "visit_count": 0,
            "last_visit": None
        }
        return {"guest_id": guest_id, **self.guests[guest_id]}

    def log_visit(self, guest_id: str, location: str = "entrance"):
        if guest_id in self.guests:
            self.guests[guest_id]["visit_count"] += 1
            self.guests[guest_id]["last_visit"] = datetime.utcnow().isoformat()
        self.visit_log.append({
            "guest_id": guest_id,
            "location": location,
            "timestamp": datetime.utcnow().isoformat()
        })

    def check_access(self, guest_id: str, zone: str) -> dict:
        if guest_id not in self.guests:
            return {"allowed": False, "reason": "Unknown guest"}
        guest = self.guests[guest_id]
        if guest["access_level"] == "blocked":
            return {"allowed": False, "reason": "Guest is blocked"}
        if guest["access_level"] == "vip":
            return {"allowed": True, "reason": "VIP access"}
        return {"allowed": True, "reason": f"Access level: {guest['access_level']}"}

    def get_active_visitors(self) -> List[dict]:
        recent = datetime.utcnow() - timedelta(hours=1)
        active = []
        for log in self.visit_log[-100:]:
            try:
                visit_time = datetime.fromisoformat(log["timestamp"])
                if visit_time >= recent:
                    guest = self.guests.get(log["guest_id"], {"name": "Unknown"})
                    active.append({**log, "name": guest.get("name", "Unknown")})
            except (ValueError, TypeError):
                pass
        return active

    def get_all_guests(self) -> dict:
        return self.guests

    def get_visit_log(self, limit: int = 50) -> List[dict]:
        return self.visit_log[-limit:]


class SleepMonitorService:
    """Feature 34: Bedtime/wake routines and sleep quality monitoring."""

    def __init__(self):
        self.sleep_sessions = []
        self.current_session = None
        self.routine_config = {
            "bedtime": {"hour": 22, "minute": 30},
            "wakeup": {"hour": 7, "minute": 0},
            "bedtime_actions": ["dim_lights", "lock_doors", "set_thermostat_night"],
            "wakeup_actions": ["gradual_lights", "play_news", "set_thermostat_day"]
        }
        logger.info("Sleep Monitor Service initialized")

    def start_sleep(self) -> dict:
        self.current_session = {
            "start": datetime.utcnow().isoformat(),
            "quality_factors": [],
            "disturbances": 0
        }
        return {"status": "sleep_started", "actions": self.routine_config["bedtime_actions"]}

    def end_sleep(self) -> dict:
        if not self.current_session:
            return {"status": "no_active_session"}
        
        start = datetime.fromisoformat(self.current_session["start"])
        duration = (datetime.utcnow() - start).total_seconds() / 3600
        
        session = {
            **self.current_session,
            "end": datetime.utcnow().isoformat(),
            "duration_hours": round(duration, 2),
            "quality_score": max(0, min(100, 80 - self.current_session["disturbances"] * 10 + 
                                        (7 - abs(duration - 8)) * 5))
        }
        self.sleep_sessions.append(session)
        self.current_session = None
        return {"status": "sleep_ended", "session": session, "actions": self.routine_config["wakeup_actions"]}

    def log_disturbance(self, reason: str = "motion"):
        if self.current_session:
            self.current_session["disturbances"] += 1
            self.current_session["quality_factors"].append({
                "type": reason, "time": datetime.utcnow().isoformat()
            })

    def get_sleep_stats(self, days: int = 7) -> dict:
        recent = self.sleep_sessions[-days:]
        if not recent:
            return {"message": "No sleep data"}
        durations = [s["duration_hours"] for s in recent]
        qualities = [s["quality_score"] for s in recent]
        return {
            "avg_duration": round(sum(durations) / len(durations), 2),
            "avg_quality": round(sum(qualities) / len(qualities), 1),
            "total_sessions": len(recent),
            "best_night": max(recent, key=lambda s: s["quality_score"]),
            "worst_night": min(recent, key=lambda s: s["quality_score"])
        }

    def get_routine_config(self) -> dict:
        return self.routine_config

    def update_routine(self, config: dict):
        self.routine_config.update(config)


class NLUService:
    """Feature 35: Natural Language Understanding with intent parsing."""

    INTENTS = {
        "turn_on": ["turn on", "switch on", "enable", "activate", "start", "power on"],
        "turn_off": ["turn off", "switch off", "disable", "deactivate", "stop", "power off"],
        "dim": ["dim", "lower", "reduce brightness", "darken"],
        "brighten": ["brighten", "increase brightness", "make brighter"],
        "status": ["status", "how is", "what is", "check", "report"],
        "temperature": ["temperature", "temp", "how hot", "how cold", "thermostat"],
        "lock": ["lock", "secure", "close lock"],
        "unlock": ["unlock", "open lock", "unsecure"],
        "capture": ["take picture", "capture", "snapshot", "photograph", "photo"],
        "schedule": ["schedule", "set timer", "remind me", "at time", "alarm"],
        "weather": ["weather", "forecast", "rain", "sunny", "temperature outside"],
        "security": ["security", "alarm", "intruder", "patrol", "guard"],
        "music": ["play music", "play song", "music", "spotify", "playlist"],
        "greeting": ["hello", "hi", "hey", "good morning", "good evening"],
        "goodbye": ["goodbye", "bye", "goodnight", "see you"],
        "help": ["help", "what can you do", "commands", "options"]
    }

    def __init__(self):
        self.context_stack = []
        logger.info("NLU Service initialized")

    def parse_intent(self, text: str) -> dict:
        """Parse user intent from natural language."""
        text_lower = text.lower().strip()
        
        best_intent = None
        best_score = 0
        matched_keywords = []
        
        for intent, keywords in self.INTENTS.items():
            for kw in keywords:
                if kw in text_lower:
                    score = len(kw) / len(text_lower)
                    if score > best_score:
                        best_score = score
                        best_intent = intent
                        matched_keywords = [kw]
        
        entities = self._extract_entities(text_lower)
        
        result = {
            "intent": best_intent or "unknown",
            "confidence": round(min(best_score * 2, 0.95), 3),
            "entities": entities,
            "matched_keywords": matched_keywords,
            "original_text": text,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.context_stack.append(result)
        if len(self.context_stack) > 20:
            self.context_stack.pop(0)
        
        return result

    def _extract_entities(self, text: str) -> dict:
        """Extract named entities from text."""
        entities = {}
        
        rooms = ["living room", "bedroom", "kitchen", "bathroom", "office", "garage", "hallway", "entrance"]
        for room in rooms:
            if room in text:
                entities["room"] = room
                break
        
        devices = ["light", "fan", "ac", "heater", "camera", "lock", "door", "window", "relay", "buzzer"]
        for device in devices:
            if device in text:
                entities["device"] = device
                break
        
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            entities["number"] = int(numbers[0])
        
        time_patterns = re.findall(r'(\d{1,2}:\d{2})', text)
        if time_patterns:
            entities["time"] = time_patterns[0]
        
        if "all" in text: entities["scope"] = "all"
        for color in ["red", "blue", "green", "white", "warm", "cool"]:
            if color in text:
                entities["color"] = color
                break
        
        return entities

    def get_context(self) -> List[dict]:
        return self.context_stack[-5:]


class ConversationContextService:
    """Feature 36: Multi-turn conversation memory."""

    def __init__(self):
        self.conversations = {}
        self.active_session = None
        logger.info("Conversation Context Service initialized")

    def start_session(self, user_id: str = "default") -> str:
        session_id = f"conv_{int(time.time())}_{user_id}"
        self.conversations[session_id] = {
            "user_id": user_id,
            "turns": [],
            "context": {},
            "started_at": datetime.utcnow().isoformat()
        }
        self.active_session = session_id
        return session_id

    def add_turn(self, session_id: str, role: str, message: str, intent: dict = None):
        if session_id not in self.conversations:
            session_id = self.start_session()
        
        self.conversations[session_id]["turns"].append({
            "role": role,
            "message": message,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if intent and intent.get("entities"):
            self.conversations[session_id]["context"].update(intent["entities"])

    def get_context(self, session_id: str) -> dict:
        if session_id not in self.conversations:
            return {}
        return self.conversations[session_id]["context"]

    def get_history(self, session_id: str, limit: int = 10) -> List[dict]:
        if session_id not in self.conversations:
            return []
        return self.conversations[session_id]["turns"][-limit:]

    def resolve_reference(self, session_id: str, text: str) -> str:
        """Resolve pronouns and references like 'it', 'that', 'there'."""
        ctx = self.get_context(session_id)
        text = text.replace("it", ctx.get("device", "it"))
        text = text.replace("there", ctx.get("room", "there"))
        return text


class HabitLearningService:
    """Feature 37: Learn and track user habits over time."""

    def __init__(self):
        self.habits = defaultdict(list)
        self.confirmed_habits = []
        logger.info("Habit Learning Service initialized")

    def record_action(self, action: str, hour: int = None, day: int = None):
        if hour is None: hour = datetime.utcnow().hour
        if day is None: day = datetime.utcnow().weekday()
        
        self.habits[action].append({
            "hour": hour, "day": day,
            "timestamp": datetime.utcnow().isoformat()
        })

    def analyze_habits(self) -> List[dict]:
        """Discover habitual patterns."""
        discovered = []
        for action, occurrences in self.habits.items():
            if len(occurrences) < 5:
                continue
            
            hours = Counter(o["hour"] for o in occurrences)
            most_common_hour, count = hours.most_common(1)[0]
            frequency = count / len(occurrences)
            
            if frequency > 0.3:
                habit = {
                    "action": action,
                    "usual_hour": most_common_hour,
                    "frequency": round(frequency, 3),
                    "total_occurrences": len(occurrences),
                    "confidence": round(min(frequency * 1.5, 0.95), 3)
                }
                discovered.append(habit)
        
        self.confirmed_habits = [h for h in discovered if h["confidence"] > 0.5]
        return discovered

    def get_habits(self) -> List[dict]:
        return self.confirmed_habits

    def get_current_suggestion(self) -> Optional[dict]:
        current_hour = datetime.utcnow().hour
        for habit in self.confirmed_habits:
            if habit["usual_hour"] == current_hour:
                return {"suggestion": f"You usually '{habit['action']}' at this time.", "habit": habit}
        return None


class EmergencyProtocolService:
    """Feature 38: Fire/intrusion/medical emergency handling."""

    def __init__(self):
        self.protocols = {
            "fire": {
                "actions": ["sound_alarm", "unlock_all_doors", "turn_on_all_lights",
                           "notify_emergency_contacts", "activate_sprinklers"],
                "priority": 1,
                "auto_call": True
            },
            "intrusion": {
                "actions": ["sound_alarm", "lock_all_doors", "turn_on_all_lights",
                           "start_recording", "notify_emergency_contacts"],
                "priority": 2,
                "auto_call": False
            },
            "medical": {
                "actions": ["notify_emergency_contacts", "unlock_front_door",
                           "turn_on_lights_path", "play_calm_music"],
                "priority": 1,
                "auto_call": True
            },
            "gas_leak": {
                "actions": ["sound_alarm", "turn_off_appliances", "open_windows",
                           "notify_emergency_contacts", "evacuate_alert"],
                "priority": 1,
                "auto_call": True
            },
            "flood": {
                "actions": ["sound_alarm", "turn_off_main_water",
                           "notify_emergency_contacts", "activate_sump_pump"],
                "priority": 2,
                "auto_call": False
            }
        }
        self.active_emergencies = []
        self.emergency_contacts = []
        self.emergency_log = []
        logger.info("Emergency Protocol Service initialized")

    def trigger_emergency(self, emergency_type: str, details: dict = None) -> dict:
        if emergency_type not in self.protocols:
            return {"error": f"Unknown emergency type: {emergency_type}"}
        
        protocol = self.protocols[emergency_type]
        emergency = {
            "type": emergency_type,
            "protocol": protocol,
            "details": details or {},
            "triggered_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        self.active_emergencies.append(emergency)
        self.emergency_log.append(emergency)
        
        logger.critical(f"EMERGENCY: {emergency_type} triggered!")
        return {
            "emergency": emergency_type,
            "actions_to_execute": protocol["actions"],
            "priority": protocol["priority"],
            "auto_call_emergency": protocol["auto_call"],
            "contacts_to_notify": self.emergency_contacts
        }

    def resolve_emergency(self, emergency_type: str) -> dict:
        self.active_emergencies = [e for e in self.active_emergencies if e["type"] != emergency_type]
        return {"status": "resolved", "type": emergency_type}

    def add_emergency_contact(self, name: str, phone: str, email: str = None):
        self.emergency_contacts.append({"name": name, "phone": phone, "email": email})

    def get_active_emergencies(self) -> List[dict]:
        return self.active_emergencies

    def get_log(self, limit: int = 50) -> List[dict]:
        return self.emergency_log[-limit:]


class GeofenceService:
    """Feature 39: Location-based automation triggers."""

    def __init__(self):
        self.zones = {}
        self.user_locations = {}
        self.triggers = []
        self.event_log = []
        logger.info("Geofence Service initialized")

    def add_zone(self, name: str, lat: float, lon: float, radius_m: float, 
                 enter_actions: list = None, exit_actions: list = None) -> dict:
        self.zones[name] = {
            "lat": lat, "lon": lon, "radius_m": radius_m,
            "enter_actions": enter_actions or [],
            "exit_actions": exit_actions or [],
            "created_at": datetime.utcnow().isoformat()
        }
        return {"zone": name, "status": "created"}

    def update_location(self, user_id: str, lat: float, lon: float) -> List[dict]:
        """Update user location and check zone transitions."""
        prev = self.user_locations.get(user_id)
        self.user_locations[user_id] = {"lat": lat, "lon": lon, "updated_at": datetime.utcnow().isoformat()}
        
        events = []
        for zone_name, zone in self.zones.items():
            in_zone = self._is_in_zone(lat, lon, zone)
            was_in_zone = self._is_in_zone(prev["lat"], prev["lon"], zone) if prev else False
            
            if in_zone and not was_in_zone:
                events.append({"event": "enter", "zone": zone_name, "actions": zone["enter_actions"]})
            elif not in_zone and was_in_zone:
                events.append({"event": "exit", "zone": zone_name, "actions": zone["exit_actions"]})
        
        self.event_log.extend(events)
        return events

    def _is_in_zone(self, lat: float, lon: float, zone: dict) -> bool:
        R = 6371000  # Earth radius in meters
        dlat = math.radians(zone["lat"] - lat)
        dlon = math.radians(zone["lon"] - lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(zone["lat"])) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = R * c
        return distance <= zone["radius_m"]

    def get_zones(self) -> dict:
        return self.zones

    def get_user_locations(self) -> dict:
        return self.user_locations


class DeviceHealthMonitor:
    """Feature 40: Monitor ESP32 and other device health."""

    def __init__(self):
        self.device_metrics = {}
        self.health_history = []
        self.alert_thresholds = {
            "cpu_temp_max": 80,
            "memory_min_pct": 10,
            "wifi_rssi_min": -80,
            "uptime_restart_threshold": 60
        }
        logger.info("Device Health Monitor initialized")

    def update_health(self, device_id: str, metrics: dict):
        """Update device health metrics."""
        self.device_metrics[device_id] = {
            **metrics,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        alerts = self._check_health(device_id, metrics)
        entry = {"device_id": device_id, "metrics": metrics, "alerts": alerts,
                 "timestamp": datetime.utcnow().isoformat()}
        self.health_history.append(entry)
        if len(self.health_history) > 5000:
            self.health_history = self.health_history[-2500:]
        return alerts

    def _check_health(self, device_id: str, metrics: dict) -> List[dict]:
        alerts = []
        if metrics.get("cpu_temp", 0) > self.alert_thresholds["cpu_temp_max"]:
            alerts.append({"type": "overheating", "value": metrics["cpu_temp"], "severity": "high"})
        if metrics.get("free_memory_pct", 100) < self.alert_thresholds["memory_min_pct"]:
            alerts.append({"type": "low_memory", "value": metrics["free_memory_pct"], "severity": "medium"})
        if metrics.get("wifi_rssi", 0) < self.alert_thresholds["wifi_rssi_min"]:
            alerts.append({"type": "weak_wifi", "value": metrics["wifi_rssi"], "severity": "low"})
        if metrics.get("uptime_seconds", 9999) < self.alert_thresholds["uptime_restart_threshold"]:
            alerts.append({"type": "recent_restart", "value": metrics["uptime_seconds"], "severity": "medium"})
        return alerts

    def get_health(self, device_id: str = None) -> dict:
        if device_id:
            return self.device_metrics.get(device_id, {})
        return self.device_metrics

    def get_health_summary(self) -> dict:
        healthy = 0
        warning = 0
        critical = 0
        for did, metrics in self.device_metrics.items():
            alerts = self._check_health(did, metrics)
            if any(a["severity"] == "high" for a in alerts): critical += 1
            elif alerts: warning += 1
            else: healthy += 1
        return {"healthy": healthy, "warning": warning, "critical": critical, "total": len(self.device_metrics)}


class TimelapseService:
    """Feature 41: Periodic frame capture for timelapse creation."""

    def __init__(self):
        self.captures = []
        self.active = False
        self.interval_seconds = 60
        self.max_captures = 1440
        logger.info("Timelapse Service initialized")

    def start(self, interval_seconds: int = 60):
        self.active = True
        self.interval_seconds = interval_seconds
        self.captures = []
        return {"status": "started", "interval": interval_seconds}

    def stop(self) -> dict:
        self.active = False
        return {"status": "stopped", "total_captures": len(self.captures)}

    def add_frame(self, frame_data: bytes, metadata: dict = None):
        if not self.active:
            return
        self.captures.append({
            "frame_size": len(frame_data),
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        })
        if len(self.captures) > self.max_captures:
            self.captures.pop(0)

    def get_status(self) -> dict:
        return {
            "active": self.active,
            "interval": self.interval_seconds,
            "captures": len(self.captures),
            "max_captures": self.max_captures
        }


class NotificationPriorityService:
    """Feature 42: Smart notification filtering and prioritization."""

    def __init__(self):
        self.rules = {
            "critical": {"min_priority": 0, "channels": ["push", "sms", "email", "alarm"]},
            "high": {"min_priority": 1, "channels": ["push", "email"]},
            "medium": {"min_priority": 2, "channels": ["push"]},
            "low": {"min_priority": 3, "channels": ["in_app"]}
        }
        self.quiet_hours = {"start": 23, "end": 7}
        self.notification_log = []
        self.suppressed_count = 0
        logger.info("Notification Priority Service initialized")

    def evaluate(self, notification: dict) -> dict:
        """Evaluate and route a notification based on priority rules."""
        severity = notification.get("severity", "low")
        hour = datetime.utcnow().hour
        is_quiet = self.quiet_hours["start"] <= hour or hour < self.quiet_hours["end"]
        
        rule = self.rules.get(severity, self.rules["low"])
        channels = rule["channels"]
        
        if is_quiet and severity not in ["critical"]:
            channels = ["in_app"]  # Suppress non-critical during quiet hours
            self.suppressed_count += 1
        
        result = {
            "notification": notification,
            "channels": channels,
            "is_quiet_hours": is_quiet,
            "suppressed": is_quiet and severity not in ["critical"],
            "timestamp": datetime.utcnow().isoformat()
        }
        self.notification_log.append(result)
        return result

    def set_quiet_hours(self, start: int, end: int):
        self.quiet_hours = {"start": start, "end": end}

    def get_stats(self) -> dict:
        return {
            "total_notifications": len(self.notification_log),
            "suppressed": self.suppressed_count,
            "quiet_hours": self.quiet_hours
        }


class BackupRestoreService:
    """Feature 43: System state backup and restore."""

    def __init__(self):
        self.backups = []
        logger.info("Backup/Restore Service initialized")

    def create_backup(self, state: dict, label: str = "auto") -> dict:
        backup = {
            "id": f"backup_{len(self.backups) + 1}_{int(time.time())}",
            "label": label,
            "state": state,
            "size_bytes": len(json.dumps(state)),
            "created_at": datetime.utcnow().isoformat()
        }
        self.backups.append(backup)
        return {"backup_id": backup["id"], "size": backup["size_bytes"], "label": label}

    def restore_backup(self, backup_id: str) -> dict:
        for backup in self.backups:
            if backup["id"] == backup_id:
                return {"status": "restored", "state": backup["state"], "label": backup["label"]}
        return {"error": "Backup not found"}

    def list_backups(self) -> List[dict]:
        return [{"id": b["id"], "label": b["label"], "size": b["size_bytes"], 
                 "created_at": b["created_at"]} for b in self.backups]

    def delete_backup(self, backup_id: str) -> bool:
        self.backups = [b for b in self.backups if b["id"] != backup_id]
        return True


class TaskSchedulerService:
    """Feature 44: Cron-like task scheduling."""

    def __init__(self):
        self.tasks = []
        self.execution_log = []
        logger.info("Task Scheduler Service initialized")

    def add_task(self, name: str, action: str, schedule: dict, params: dict = None) -> dict:
        task = {
            "id": len(self.tasks) + 1,
            "name": name,
            "action": action,
            "schedule": schedule,  # {"type": "interval|cron|once", "value": ...}
            "params": params or {},
            "enabled": True,
            "last_run": None,
            "run_count": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        self.tasks.append(task)
        return task

    def get_due_tasks(self) -> List[dict]:
        """Get tasks that should run now."""
        now = datetime.utcnow()
        due = []
        for task in self.tasks:
            if not task["enabled"]:
                continue
            schedule = task["schedule"]
            if schedule.get("type") == "interval":
                interval = timedelta(seconds=schedule.get("value", 3600))
                last_run = datetime.fromisoformat(task["last_run"]) if task["last_run"] else datetime.min
                if now - last_run >= interval:
                    due.append(task)
            elif schedule.get("type") == "once":
                run_at = datetime.fromisoformat(schedule.get("value", ""))
                if now >= run_at and not task["last_run"]:
                    due.append(task)
        return due

    def mark_executed(self, task_id: int):
        for task in self.tasks:
            if task["id"] == task_id:
                task["last_run"] = datetime.utcnow().isoformat()
                task["run_count"] += 1
                self.execution_log.append({
                    "task_id": task_id, "name": task["name"],
                    "executed_at": datetime.utcnow().isoformat()
                })

    def get_tasks(self) -> List[dict]:
        return self.tasks

    def toggle_task(self, task_id: int) -> bool:
        for task in self.tasks:
            if task["id"] == task_id:
                task["enabled"] = not task["enabled"]
                return task["enabled"]
        return False

    def get_execution_log(self, limit: int = 50) -> List[dict]:
        return self.execution_log[-limit:]


class SmartLightingService:
    """Feature 45: Intelligent lighting automation."""

    def __init__(self):
        self.room_lights = {}
        self.schedules = []
        self.ambient_mode = False
        self.circadian_mode = True
        logger.info("Smart Lighting Service initialized")

    def set_room_light(self, room: str, brightness: int = 100, 
                       color_temp: int = 4000, color: str = None) -> dict:
        self.room_lights[room] = {
            "brightness": max(0, min(100, brightness)),
            "color_temp": color_temp,
            "color": color,
            "updated_at": datetime.utcnow().isoformat()
        }
        return self.room_lights[room]

    def get_circadian_setting(self) -> dict:
        """Get recommended light settings based on time of day."""
        hour = datetime.utcnow().hour
        if 6 <= hour < 9:
            return {"brightness": 60, "color_temp": 3000, "label": "sunrise_warm"}
        elif 9 <= hour < 12:
            return {"brightness": 90, "color_temp": 5000, "label": "morning_bright"}
        elif 12 <= hour < 17:
            return {"brightness": 100, "color_temp": 5500, "label": "daylight"}
        elif 17 <= hour < 20:
            return {"brightness": 70, "color_temp": 3500, "label": "evening_warm"}
        elif 20 <= hour < 22:
            return {"brightness": 40, "color_temp": 2700, "label": "night_dim"}
        else:
            return {"brightness": 10, "color_temp": 2200, "label": "sleep_very_dim"}

    def get_all_rooms(self) -> dict:
        return self.room_lights

    def all_off(self) -> dict:
        for room in self.room_lights:
            self.room_lights[room]["brightness"] = 0
        return {"status": "all_lights_off"}

    def all_on(self, brightness: int = 100) -> dict:
        for room in self.room_lights:
            self.room_lights[room]["brightness"] = brightness
        return {"status": "all_lights_on", "brightness": brightness}


# Singleton instances
scene_memory = SceneMemoryService()
predictive_service = PredictiveAutomationService()
calendar_service = CalendarService()
guest_service = GuestManagementService()
sleep_service = SleepMonitorService()
nlu_service = NLUService()
conversation_service = ConversationContextService()
habit_service = HabitLearningService()
emergency_service = EmergencyProtocolService()
geofence_service = GeofenceService()
device_health_monitor = DeviceHealthMonitor()
timelapse_service = TimelapseService()
notification_priority_service = NotificationPriorityService()
backup_service = BackupRestoreService()
task_scheduler = TaskSchedulerService()
smart_lighting = SmartLightingService()
