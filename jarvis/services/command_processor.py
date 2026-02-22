"""
Jarvis AI - Command Processor
================================
Advanced natural language command parsing and routing.
Maps voice/text commands to actions across all services.
"""
import re
from typing import Optional, Dict, Tuple
from datetime import datetime

from loguru import logger

from jarvis.config import settings


class CommandCategory:
    HOME = "home"
    SECURITY = "security"
    SYSTEM = "system"
    CAMERA = "camera"
    CONVERSATION = "conversation"
    INFORMATION = "information"
    FACE = "face"
    UNKNOWN = "unknown"


# Pattern → (category, action, params_extractor)
COMMAND_PATTERNS = [
    # ---- Home Automation ----
    (r"turn\s+(on|off)\s+(?:the\s+)?(.*?)(?:\s+light[s]?|\s+relay)?$", CommandCategory.HOME, "toggle_device"),
    (r"(switch|set)\s+(on|off)\s+(?:the\s+)?(.*)", CommandCategory.HOME, "toggle_device"),
    (r"all\s+lights?\s+(on|off)", CommandCategory.HOME, "all_lights"),
    (r"(turn|switch)\s+(on|off)\s+(?:all|everything)", CommandCategory.HOME, "all_lights"),
    (r"relay\s+(\d+)\s+(on|off)", CommandCategory.HOME, "relay_number"),
    (r"scene\s+(\d+)", CommandCategory.HOME, "scene"),
    (r"save\s+scene\s+(\d+)", CommandCategory.HOME, "save_scene"),
    (r"(?:what(?:'s| is)\s+the\s+)?temperature", CommandCategory.HOME, "temperature"),
    (r"(?:what(?:'s| is)\s+the\s+)?humidity", CommandCategory.HOME, "humidity"),
    (r"(?:power|voltage|current|electricity)", CommandCategory.HOME, "power"),
    (r"(buzz|beep|alarm|alert)", CommandCategory.HOME, "buzzer"),

    # ---- Security ----
    (r"(?:any\s+)?intruder[s]?", CommandCategory.SECURITY, "intruder_check"),
    (r"security\s+(?:status|report|check)", CommandCategory.SECURITY, "security_status"),
    (r"who\s+(?:came|entered|visited|was\s+here)", CommandCategory.SECURITY, "visitor_log"),
    (r"show\s+(?:intruder|security)\s+(?:photos?|images?|records?)", CommandCategory.SECURITY, "intruder_gallery"),
    (r"lock\s*down", CommandCategory.SECURITY, "lockdown"),

    # ---- Camera ----
    (r"(?:take|capture)\s+(?:a\s+)?(?:photo|picture|snapshot|image)", CommandCategory.CAMERA, "snapshot"),
    (r"start\s+recording", CommandCategory.CAMERA, "start_recording"),
    (r"stop\s+recording", CommandCategory.CAMERA, "stop_recording"),
    (r"show\s+(?:the\s+)?(?:camera|video|feed|live)", CommandCategory.CAMERA, "live_feed"),

    # ---- Face Recognition ----
    (r"(?:register|learn|remember|save)\s+(?:my\s+)?face", CommandCategory.FACE, "register_face"),
    (r"who\s+am\s+i", CommandCategory.FACE, "identify"),
    (r"identify\s+(?:me|this\s+person)", CommandCategory.FACE, "identify"),
    (r"(?:add|register)\s+(?:a\s+)?(?:new\s+)?(?:person|face|user)\s+(.*)", CommandCategory.FACE, "register_person"),
    (r"how\s+many\s+faces?\s+(?:do\s+you\s+)?know", CommandCategory.FACE, "face_count"),

    # ---- System ----
    (r"(?:system\s+)?status", CommandCategory.SYSTEM, "status"),
    (r"how\s+are\s+you", CommandCategory.SYSTEM, "status"),
    (r"go\s+to\s+sleep|sleep\s+mode|goodnight|good\s+night", CommandCategory.SYSTEM, "sleep"),
    (r"wake\s+up|good\s+morning", CommandCategory.SYSTEM, "wake"),
    (r"shut\s*down|power\s+off|stop", CommandCategory.SYSTEM, "shutdown"),
    (r"restart|reboot", CommandCategory.SYSTEM, "restart"),
    (r"what\s+can\s+you\s+do|help|commands", CommandCategory.SYSTEM, "help"),
    (r"version|about", CommandCategory.SYSTEM, "about"),
    (r"mute|quiet|silent", CommandCategory.SYSTEM, "mute"),
    (r"unmute|speak|talk", CommandCategory.SYSTEM, "unmute"),

    # ---- Information ----
    (r"what\s+time\s+is\s+it|(?:current\s+)?time", CommandCategory.INFORMATION, "time"),
    (r"what(?:'s| is)\s+(?:today(?:'s)?\s+)?date|today", CommandCategory.INFORMATION, "date"),
    (r"(?:what(?:'s| is)\s+the\s+)?weather", CommandCategory.INFORMATION, "weather"),

    # ---- Conversation ----
    (r"^(?:hello|hi|hey|greetings)\b", CommandCategory.CONVERSATION, "greeting"),
    (r"(?:thank|thanks)", CommandCategory.CONVERSATION, "thanks"),
    (r"(?:bye|goodbye|see\s+you|later)", CommandCategory.CONVERSATION, "farewell"),
    (r"(?:good|nice|great|awesome|cool|perfect)", CommandCategory.CONVERSATION, "positive"),
    (r"(?:sorry|oops|my\s+bad)", CommandCategory.CONVERSATION, "apology"),
]


class CommandProcessor:
    """Parses and categorizes natural language commands."""

    def __init__(self):
        self._compiled = [(re.compile(p, re.IGNORECASE), cat, action) for p, cat, action in COMMAND_PATTERNS]
        self._history: list = []
        logger.info(f"Command processor loaded with {len(self._compiled)} patterns")

    def parse(self, text: str) -> Dict:
        """Parse a command into category, action, and extracted params."""
        text = text.strip()
        if not text:
            return {"category": CommandCategory.UNKNOWN, "action": "empty", "params": {}, "raw": text}

        for pattern, category, action in self._compiled:
            match = pattern.search(text)
            if match:
                params = {"groups": match.groups(), "match": match.group(0)}
                result = {
                    "category": category,
                    "action": action,
                    "params": params,
                    "raw": text,
                    "confidence": 1.0,
                }
                self._history.append(result)
                return result

        # Fallback — unknown
        result = {
            "category": CommandCategory.UNKNOWN,
            "action": "unknown",
            "params": {},
            "raw": text,
            "confidence": 0.0,
        }
        self._history.append(result)
        return result

    def extract_device_info(self, parsed: Dict) -> Tuple[Optional[str], Optional[bool]]:
        """Extract device name and desired state from a parsed command."""
        groups = parsed.get("params", {}).get("groups", ())
        action = parsed.get("action", "")

        if action == "toggle_device" and len(groups) >= 2:
            state_word = groups[0].lower()
            device = groups[1].strip() if len(groups) > 1 else groups[-1].strip()
            state = state_word in ("on", "enable", "activate")
            return device, state

        if action == "all_lights" and len(groups) >= 1:
            state = groups[0].lower() in ("on",)
            return "all", state

        if action == "relay_number" and len(groups) >= 2:
            relay_num = groups[0]
            state = groups[1].lower() in ("on",)
            return f"relay_{relay_num}", state

        return None, None

    def get_help_text(self) -> str:
        """Return a summary of available commands."""
        return (
            "I can help you with: "
            "Lights and relays — say 'turn on living room light' or 'all lights off'. "
            "Temperature and sensors — say 'what's the temperature'. "
            "Security — say 'any intruders' or 'security status'. "
            "Camera — say 'take a photo' or 'start recording'. "
            "Face recognition — say 'register my face' or 'who am I'. "
            "System — say 'status', 'go to sleep', or 'wake up'. "
            "Time — say 'what time is it' or 'what's today's date'."
        )

    def get_history(self, limit: int = 20) -> list:
        return self._history[-limit:]


# Singleton
command_processor = CommandProcessor()
