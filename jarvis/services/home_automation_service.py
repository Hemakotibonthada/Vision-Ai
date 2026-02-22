w"""
Jarvis AI - Home Automation Service
======================================
Controls ESP32 relays, sensors, and smart home devices.
Bridges Jarvis commands to the ESP32 server.
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
    """Controls smart home devices via ESP32 server."""

    def __init__(self):
        self.base_url = f"{settings.ESP32_SERVER_URL}{settings.ESP32_API_PREFIX}"
        self._device_states: Dict = {}
        self._sensor_data: Dict = {}
        self._last_sensor_read = 0
        self._room_names = [
            "Living Room", "Bedroom", "Kitchen", "Bathroom",
            "Garage", "Porch", "Study", "Spare"
        ]
        logger.info(f"Home automation service initialized. ESP32: {settings.ESP32_SERVER_URL}")

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
    # Natural Language Command Processing
    # ================================================================
    async def process_command(self, command: str) -> str:
        """Process a natural language home command.
        
        e.g., "turn on the living room lights"
             "switch off all lights"
             "what's the temperature"
        """
        command = command.lower().strip()

        # ---- All lights/relays ----
        if any(w in command for w in ["all lights on", "turn on everything", "all on"]):
            await self.set_all_relays(True)
            return "All lights turned on."

        if any(w in command for w in ["all lights off", "turn off everything", "all off"]):
            await self.set_all_relays(False)
            return "All lights turned off."

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
