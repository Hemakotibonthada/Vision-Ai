"""
Jarvis AI - Home Automation Service v3.0
==========================================
Controls ESP32 relays, sensors, door, lock, schedules, camera,
and smart home devices. Bridges Jarvis commands to ESP32 boards.
Integrates with MQTT bridge and ESP32 manager services.
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Optional, List

import httpx
from loguru import logger

from jarvis.config import settings


class HomeAutomationService:
    """Controls smart home devices via ESP32 server and camera."""

    def __init__(self):
        self.base_url = f"{settings.ESP32_SERVER_URL}{settings.ESP32_API_PREFIX}"
        self.cam_url = getattr(settings, "ESP32_CAM_URL", "http://192.168.1.102")
        self._device_states: Dict = {}
        self._sensor_data: Dict = {}
        self._door_state: str = "unknown"
        self._lock_state: str = "unknown"
        self._last_sensor_read = 0
        self._last_heartbeat: Dict = {}
        self._schedules: List[Dict] = []
        self._room_names = [
            "Living Room", "Bedroom", "Kitchen", "Bathroom",
            "Garage", "Porch", "Study", "Spare"
        ]
        self._mqtt_bridge = None
        self._esp32_manager = None
        logger.info(f"Home automation service v3.0 initialized. ESP32: {settings.ESP32_SERVER_URL}")

    def set_mqtt_bridge(self, bridge):
        """Set MQTT bridge reference for real-time control."""
        self._mqtt_bridge = bridge
        logger.info("MQTT bridge linked to home automation service")

    def set_esp32_manager(self, manager):
        """Set ESP32 manager reference."""
        self._esp32_manager = manager
        logger.info("ESP32 manager linked to home automation service")

    # ================================================================
    # Relay / Switch Control
    # ================================================================
    async def set_relay(self, relay: int, state: bool) -> Dict:
        """Turn a relay on/off."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/gpio/relay",
                    params={"relay": relay, "state": 1 if state else 0}
                )
                result = resp.json()
                self._device_states[f"relay_{relay}"] = state
                logger.info(f"Relay {relay}: {'ON' if state else 'OFF'}")
                return result
        except Exception as e:
            logger.error(f"Set relay failed: {e}")
            return {"error": str(e)}

    async def set_relay_by_room(self, room: str, state: bool) -> Dict:
        """Control a relay by room name."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/gpio/relay/room",
                    params={"room": room, "state": 1 if state else 0}
                )
                result = resp.json()
                logger.info(f"Room '{room}': {'ON' if state else 'OFF'}")
                return result
        except Exception as e:
            logger.error(f"Set room relay failed: {e}")
            return {"error": str(e)}

    async def set_all_relays(self, state: bool) -> Dict:
        """Turn all relays on/off."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/gpio/relay/all",
                    params={"state": 1 if state else 0}
                )
                return resp.json()
        except Exception as e:
            logger.error(f"Set all relays failed: {e}")
            return {"error": str(e)}

    async def get_relay_status(self) -> Dict:
        """Get current status of all relays."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/gpio/status")
                self._device_states = resp.json()
                return self._device_states
        except Exception as e:
            logger.error(f"Get relay status failed: {e}")
            return {"error": str(e)}

    # ================================================================
    # Scene Control
    # ================================================================
    async def save_scene(self, scene_id: int) -> Dict:
        """Save current relay states as a scene."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/gpio/scene/save",
                    params={"scene": scene_id}
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def load_scene(self, scene_id: int) -> Dict:
        """Load a saved scene."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/gpio/scene/load",
                    params={"scene": scene_id}
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ================================================================
    # Sensor Data
    # ================================================================
    async def get_sensors(self) -> Dict:
        """Read all sensor data from ESP32."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/sensors")
                self._sensor_data = resp.json()
                self._last_sensor_read = time.time()
                return self._sensor_data
        except Exception as e:
            logger.error(f"Get sensors failed: {e}")
            return {"error": str(e)}

    async def get_temperature(self) -> Optional[float]:
        data = await self.get_sensors()
        return data.get("temperature")

    async def get_humidity(self) -> Optional[float]:
        data = await self.get_sensors()
        return data.get("humidity")

    async def get_power_data(self) -> Dict:
        """Get voltage/current/power readings."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/sensors/power")
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ================================================================
    # Buzzer Control
    # ================================================================
    async def buzz(self, pattern: str = "alert") -> Dict:
        """Trigger buzzer pattern on ESP32."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/gpio/buzzer",
                    params={"pattern": pattern}
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ================================================================
    # Door Sensor
    # ================================================================
    async def get_door_status(self) -> Dict:
        """Get door sensor and lock status."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/door/status")
                data = resp.json()
                self._door_state = data.get("door", "unknown")
                self._lock_state = data.get("lock", "unknown")
                return data
        except Exception as e:
            logger.error(f"Get door status failed: {e}")
            return {"error": str(e)}

    def is_door_open(self) -> bool:
        return self._door_state == "open"

    def is_locked(self) -> bool:
        return self._lock_state == "locked"

    # ================================================================
    # Servo Lock Control
    # ================================================================
    async def set_lock(self, locked: bool) -> Dict:
        """Lock or unlock the door."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/lock/set",
                    params={"state": "1" if locked else "0"}
                )
                result = resp.json()
                self._lock_state = "locked" if locked else "unlocked"
                logger.info(f"Lock: {'LOCKED' if locked else 'UNLOCKED'}")
                return result
        except Exception as e:
            logger.error(f"Set lock failed: {e}")
            return {"error": str(e)}

    async def toggle_lock(self) -> Dict:
        """Toggle lock state."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(f"{self.base_url}/lock/toggle")
                result = resp.json()
                self._lock_state = result.get("lock", "unknown")
                return result
        except Exception as e:
            return {"error": str(e)}

    # ================================================================
    # Schedule Management
    # ================================================================
    async def get_schedules(self) -> List[Dict]:
        """Get all active schedules."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/schedules")
                data = resp.json()
                self._schedules = data.get("schedules", [])
                return self._schedules
        except Exception as e:
            logger.error(f"Get schedules failed: {e}")
            return []

    async def add_schedule(self, relay: int, hour: int, minute: int,
                           action: int = 1, days: int = 0x7F,
                           repeat: int = 1) -> Dict:
        """Add a new automation schedule."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/schedules/add",
                    params={
                        "relay": relay, "hour": hour, "minute": minute,
                        "action": action, "days": days, "repeat": repeat
                    }
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def delete_schedule(self, schedule_id: int) -> Dict:
        """Delete a schedule."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/schedules/delete",
                    params={"id": schedule_id}
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ================================================================
    # Camera Integration
    # ================================================================
    async def get_camera_status(self) -> Dict:
        """Get ESP32-CAM status."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.cam_url}/jarvis/status")
                return resp.json()
        except Exception as e:
            logger.error(f"Camera status failed: {e}")
            return {"error": str(e)}

    async def camera_capture(self) -> Optional[bytes]:
        """Capture a JPEG image from the camera."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.cam_url}/capture")
                if resp.status_code == 200:
                    return resp.content
        except Exception as e:
            logger.error(f"Camera capture failed: {e}")
        return None

    async def camera_detect(self) -> Dict:
        """Trigger AI detection on camera."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{self.cam_url}/jarvis/detect")
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_stream_url(self) -> str:
        """Get the MJPEG stream URL."""
        return f"{self.cam_url}:81/stream"

    # ================================================================
    # Jarvis Heartbeat
    # ================================================================
    async def get_heartbeat(self) -> Dict:
        """Get full device heartbeat from ESP32 server."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/jarvis/heartbeat")
                self._last_heartbeat = resp.json()
                return self._last_heartbeat
        except Exception as e:
            return {"error": str(e)}

    def get_cached_heartbeat(self) -> Dict:
        return self._last_heartbeat

    # ================================================================
    # Natural Language Command Processing
    # ================================================================
    async def process_command(self, command: str) -> str:
        """Process a natural language home command.
        
        Supports: relay control, room control, door/lock, schedules,
                  camera, sensors, scenes, buzzer, and more.
        """
        command = command.lower().strip()

        # ---- All lights/relays ----
        if any(w in command for w in ["all lights on", "turn on everything", "all on"]):
            await self.set_all_relays(True)
            return "All lights turned on."

        if any(w in command for w in ["all lights off", "turn off everything", "all off"]):
            await self.set_all_relays(False)
            return "All lights turned off."

        # ---- Door ----
        if any(w in command for w in ["door status", "is the door", "door open", "door closed"]):
            data = await self.get_door_status()
            door = data.get("door", "unknown")
            lock = data.get("lock", "unknown")
            return f"The door is {door}. The lock is {lock}."

        # ---- Lock ----
        if any(w in command for w in ["lock the door", "lock door", "lock up", "engage lock"]):
            await self.set_lock(True)
            return "Door locked."

        if any(w in command for w in ["unlock the door", "unlock door", "unlock", "disengage lock"]):
            await self.set_lock(False)
            return "Door unlocked."

        # ---- Camera ----
        if any(w in command for w in ["take a photo", "capture image", "take picture", "snapshot"]):
            result = await self.camera_detect()
            if "error" not in result:
                return f"Image captured and processed. AI result: {json.dumps(result)[:200]}"
            return "Failed to capture image."

        if any(w in command for w in ["camera status", "cam status"]):
            status = await self.get_camera_status()
            if "error" not in status:
                streaming = status.get("streaming", False)
                persons = status.get("persons", 0)
                night = status.get("night_mode", False)
                return f"Camera: {'streaming' if streaming else 'idle'}, {persons} person(s), night mode {'on' if night else 'off'}."
            return "Camera unavailable."

        if "stream" in command and "url" in command:
            return f"Camera stream: {self.get_stream_url()}"

        # ---- Schedule ----
        if any(w in command for w in ["show schedules", "list schedules", "what schedules"]):
            schedules = await self.get_schedules()
            if schedules:
                lines = []
                for s in schedules:
                    lines.append(f"  #{s.get('id', '?')}: Relay {s.get('relay', '?')} at {s.get('hour', 0):02d}:{s.get('minute', 0):02d}")
                return "Active schedules:\n" + "\n".join(lines)
            return "No schedules configured."

        # ---- Heartbeat / System ----
        if any(w in command for w in ["system status", "heartbeat", "device health"]):
            hb = await self.get_heartbeat()
            if "error" not in hb:
                return (f"ESP32 Server: up {hb.get('uptime', 0)}s, "
                        f"heap {hb.get('free_heap', 0)} bytes, "
                        f"RSSI {hb.get('rssi', 0)} dBm, "
                        f"door {hb.get('door', '?')}, "
                        f"lock {hb.get('lock', '?')}, "
                        f"temp {hb.get('temperature', '?')}°C, "
                        f"{hb.get('schedules', 0)} schedules active.")
            return "Could not reach ESP32 server."

        # ---- Room-specific ----
        for room in self._room_names:
            room_lower = room.lower()
            if room_lower in command:
                if any(w in command for w in ["on", "turn on", "switch on", "enable"]):
                    await self.set_relay_by_room(room, True)
                    return f"{room} light turned on."
                elif any(w in command for w in ["off", "turn off", "switch off", "disable"]):
                    await self.set_relay_by_room(room, False)
                    return f"{room} light turned off."

        # ---- Numbered relay ----
        for i in range(1, 9):
            words = [f"relay {i}", f"switch {i}", f"light {i}"]
            if any(w in command for w in words):
                if any(w in command for w in ["on", "turn on", "enable"]):
                    await self.set_relay(i, True)
                    return f"Relay {i} turned on."
                elif any(w in command for w in ["off", "turn off", "disable"]):
                    await self.set_relay(i, False)
                    return f"Relay {i} turned off."

        # ---- Temperature ----
        if any(w in command for w in ["temperature", "temp", "how hot", "how cold"]):
            data = await self.get_sensors()
            temp = data.get("temperature", "unknown")
            hum = data.get("humidity", "unknown")
            return f"The temperature is {temp} degrees Celsius with {hum} percent humidity."

        # ---- Power ----
        if any(w in command for w in ["voltage", "current", "power", "electricity"]):
            data = await self.get_power_data()
            v = data.get("voltage", "unknown")
            c = data.get("current", "unknown")
            p = data.get("power", "unknown")
            return f"Voltage is {v} volts, current is {c} amps, power consumption is {p} watts."

        # ---- Scene ----
        if "scene" in command or "mood" in command:
            for i in range(5):
                if str(i) in command or ["one", "two", "three", "four", "five"][i] in command:
                    if "save" in command:
                        await self.save_scene(i)
                        return f"Scene {i} saved."
                    else:
                        await self.load_scene(i)
                        return f"Scene {i} activated."

        # ---- Status ----
        if any(w in command for w in ["status", "devices", "what's on"]):
            status = await self.get_relay_status()
            return f"Device status: {json.dumps(status, indent=2)}"

        # ---- Buzzer ----
        if any(w in command for w in ["alarm", "alert", "buzz", "beep"]):
            await self.buzz("alert")
            return "Alert buzzer activated."

        return "I'm not sure how to handle that home command."

    def get_room_names(self) -> List[str]:
        return self._room_names

    def get_cached_sensors(self) -> Dict:
        return self._sensor_data


# Singleton
home_service = HomeAutomationService()
