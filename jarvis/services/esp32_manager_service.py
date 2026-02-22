"""
Vision-AI ESP32 Device Manager Service v3.0
Manages ESP32 Server + ESP32-CAM boards via HTTP and MQTT.
Provides unified interface for device control, monitoring, and OTA.
"""

import json
import time
import asyncio
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field

try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger("jarvis.esp32_manager")


@dataclass
class ESP32Device:
    """Represents a physical ESP32 device."""
    device_id: str
    device_type: str  # "server" or "camera"
    ip: str = ""
    http_port: int = 80
    api_prefix: str = "/api/v1"
    online: bool = False
    firmware: str = ""
    last_seen: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)


class ESP32ManagerService:
    """
    Unified management of all ESP32 devices in the Vision-AI system.
    Supports both HTTP REST API calls and MQTT command routing.
    """

    def __init__(self, mqtt_bridge=None):
        self.mqtt_bridge = mqtt_bridge
        self.devices: Dict[str, ESP32Device] = {}
        self._health_check_interval = 30  # seconds
        self._running = False

        # Register default devices
        self.register_device(ESP32Device(
            device_id="esp32-server-01",
            device_type="server",
            ip="192.168.1.101",
            http_port=80,
            api_prefix="/api/v1",
            capabilities=["relays", "sensors", "door", "lock", "schedules",
                          "buzzer", "ble", "ota", "mqtt", "websocket"]
        ))
        self.register_device(ESP32Device(
            device_id="esp32-cam-01",
            device_type="camera",
            ip="192.168.1.102",
            http_port=80,
            api_prefix="",
            capabilities=["capture", "stream", "motion", "face_detect",
                          "night_vision", "patrol", "intruder", "ai_upload"]
        ))

    def register_device(self, device: ESP32Device):
        """Register a new ESP32 device."""
        self.devices[device.device_id] = device
        logger.info(f"Registered device: {device.device_id} ({device.device_type}) at {device.ip}")

    def update_device_from_heartbeat(self, data: Dict):
        """Update device state from a heartbeat message."""
        device_id = data.get("device", "")
        for dev in self.devices.values():
            if dev.device_id == device_id or dev.ip == data.get("ip", ""):
                dev.online = True
                dev.last_seen = time.time()
                dev.firmware = data.get("firmware", dev.firmware)
                dev.ip = data.get("ip", dev.ip)
                dev.state = data
                break

    # =========================================
    # HTTP API Helpers
    # =========================================

    async def _http_get(self, device_id: str, path: str, timeout: int = 10) -> Optional[Dict]:
        """Make HTTP GET request to a device."""
        if aiohttp is None:
            logger.error("aiohttp not installed")
            return None

        dev = self.devices.get(device_id)
        if not dev:
            logger.error(f"Device not found: {device_id}")
            return None

        url = f"http://{dev.ip}:{dev.http_port}{dev.api_prefix}{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        logger.warning(f"HTTP GET {url} returned {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"HTTP GET {url} failed: {e}")
            dev.online = False
            return None

    async def _http_post(self, device_id: str, path: str,
                         params: Dict = None, timeout: int = 10) -> Optional[Dict]:
        """Make HTTP POST request to a device."""
        if aiohttp is None:
            logger.error("aiohttp not installed")
            return None

        dev = self.devices.get(device_id)
        if not dev:
            logger.error(f"Device not found: {device_id}")
            return None

        url = f"http://{dev.ip}:{dev.http_port}{dev.api_prefix}{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params,
                                        timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        logger.warning(f"HTTP POST {url} returned {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"HTTP POST {url} failed: {e}")
            dev.online = False
            return None

    # =========================================
    # ESP32 Server Control (HTTP)
    # =========================================

    async def get_server_status(self) -> Optional[Dict]:
        """Get full status from ESP32 server."""
        return await self._http_get("esp32-server-01", "/status")

    async def get_sensors(self) -> Optional[Dict]:
        """Get sensor readings."""
        return await self._http_get("esp32-server-01", "/sensors")

    async def set_relay(self, relay_id: int, state: bool) -> Optional[Dict]:
        """Control a specific relay."""
        return await self._http_post("esp32-server-01", f"/relay/{relay_id}",
                                     {"state": "1" if state else "0"})

    async def toggle_relay(self, relay_id: int) -> Optional[Dict]:
        """Toggle a relay."""
        return await self._http_post("esp32-server-01", f"/relay/{relay_id}/toggle")

    async def set_all_relays(self, state: bool) -> Optional[Dict]:
        """Set all relays to the same state."""
        return await self._http_post("esp32-server-01", "/relays/all",
                                     {"state": "1" if state else "0"})

    async def get_door_status(self) -> Optional[Dict]:
        """Get door sensor status."""
        return await self._http_get("esp32-server-01", "/door/status")

    async def set_lock(self, locked: bool) -> Optional[Dict]:
        """Control the servo lock."""
        return await self._http_post("esp32-server-01", "/lock/set",
                                     {"state": "1" if locked else "0"})

    async def toggle_lock(self) -> Optional[Dict]:
        """Toggle the lock."""
        return await self._http_post("esp32-server-01", "/lock/toggle")

    async def get_schedules(self) -> Optional[Dict]:
        """Get all schedules."""
        return await self._http_get("esp32-server-01", "/schedules")

    async def add_schedule(self, relay: int, hour: int, minute: int,
                           action: int = 1, days: int = 0x7F,
                           repeat: int = 1) -> Optional[Dict]:
        """Add a new schedule."""
        return await self._http_post("esp32-server-01", "/schedules/add", {
            "relay": str(relay), "hour": str(hour), "minute": str(minute),
            "action": str(action), "days": str(days), "repeat": str(repeat)
        })

    async def delete_schedule(self, schedule_id: int) -> Optional[Dict]:
        """Delete a schedule."""
        return await self._http_post("esp32-server-01", "/schedules/delete",
                                     {"id": str(schedule_id)})

    async def get_heartbeat(self) -> Optional[Dict]:
        """Get Jarvis heartbeat from server."""
        return await self._http_get("esp32-server-01", "/jarvis/heartbeat")

    async def buzz(self, pattern: str = "alert") -> Optional[Dict]:
        """Trigger buzzer."""
        return await self._http_post("esp32-server-01", "/buzz",
                                     {"pattern": pattern})

    # =========================================
    # ESP32-CAM Control (HTTP)
    # =========================================

    async def get_camera_status(self) -> Optional[Dict]:
        """Get camera status."""
        return await self._http_get("esp32-cam-01", "/status")

    async def get_jarvis_cam_status(self) -> Optional[Dict]:
        """Get Jarvis-specific camera status."""
        dev = self.devices.get("esp32-cam-01")
        if not dev:
            return None
        url = f"http://{dev.ip}:{dev.http_port}/jarvis/status"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Camera jarvis status failed: {e}")
        return None

    async def trigger_detection(self) -> Optional[Dict]:
        """Trigger a capture + AI detection."""
        dev = self.devices.get("esp32-cam-01")
        if not dev:
            return None
        url = f"http://{dev.ip}:{dev.http_port}/jarvis/detect"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Camera detect failed: {e}")
        return None

    async def get_capture_url(self) -> Optional[str]:
        """Get the camera capture URL."""
        dev = self.devices.get("esp32-cam-01")
        if dev and dev.ip:
            return f"http://{dev.ip}:{dev.http_port}/capture"
        return None

    async def get_stream_url(self) -> Optional[str]:
        """Get the camera stream URL."""
        dev = self.devices.get("esp32-cam-01")
        if dev and dev.ip:
            return f"http://{dev.ip}:81/stream"
        return None

    async def capture_image(self) -> Optional[bytes]:
        """Capture a JPEG image from the camera."""
        dev = self.devices.get("esp32-cam-01")
        if not dev:
            return None
        url = f"http://{dev.ip}:{dev.http_port}/capture"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            logger.error(f"Image capture failed: {e}")
        return None

    # =========================================
    # MQTT-Based Control (via Bridge)
    # =========================================

    def mqtt_set_relay(self, relay_id: int, state: bool) -> bool:
        """Control relay via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.set_relay(relay_id, state)
        return False

    def mqtt_set_lock(self, locked: bool) -> bool:
        """Control lock via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.set_lock(locked)
        return False

    def mqtt_capture(self, context: str = "jarvis") -> bool:
        """Trigger camera capture via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.trigger_capture(context)
        return False

    def mqtt_start_patrol(self) -> bool:
        """Start patrol mode via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.start_patrol()
        return False

    def mqtt_stop_patrol(self) -> bool:
        """Stop patrol mode via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.stop_patrol()
        return False

    def mqtt_intruder_mode(self, enabled: bool) -> bool:
        """Enable/disable intruder mode via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.set_intruder_mode(enabled)
        return False

    def mqtt_identify(self) -> bool:
        """Request face identification via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.request_identify()
        return False

    def mqtt_scene(self, scene: str) -> bool:
        """Activate a scene via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.activate_scene(scene)
        return False

    def mqtt_buzz(self, pattern: str = "alert") -> bool:
        """Trigger buzzer via MQTT."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.buzz_alert(pattern)
        return False

    # =========================================
    # Health Monitoring
    # =========================================

    def get_device_health(self) -> Dict[str, Dict]:
        """Get health status for all devices."""
        result = {}
        now = time.time()
        for dev_id, dev in self.devices.items():
            stale = (now - dev.last_seen) > 45 if dev.last_seen > 0 else True
            result[dev_id] = {
                "device_id": dev.device_id,
                "type": dev.device_type,
                "ip": dev.ip,
                "online": dev.online and not stale,
                "firmware": dev.firmware,
                "last_seen": dev.last_seen,
                "age_seconds": int(now - dev.last_seen) if dev.last_seen > 0 else -1,
                "capabilities": dev.capabilities,
                "state_keys": list(dev.state.keys()) if dev.state else []
            }
        return result

    async def health_check(self) -> Dict[str, bool]:
        """Ping all devices to check if they're reachable."""
        results = {}
        for dev_id, dev in self.devices.items():
            try:
                if dev.device_type == "server":
                    data = await self._http_get(dev_id, "/status")
                else:
                    data = await self._http_get(dev_id, "/status")
                if data:
                    dev.online = True
                    dev.last_seen = time.time()
                    results[dev_id] = True
                else:
                    dev.online = False
                    results[dev_id] = False
            except Exception:
                dev.online = False
                results[dev_id] = False
        return results

    def get_summary(self) -> Dict:
        """Get a summary of all managed devices."""
        server_state = {}
        cam_state = {}
        for dev in self.devices.values():
            if dev.device_type == "server":
                server_state = dev.state
            elif dev.device_type == "camera":
                cam_state = dev.state

        return {
            "devices": len(self.devices),
            "online": sum(1 for d in self.devices.values() if d.online),
            "server": {
                "online": server_state.get("device") is not None,
                "relays": server_state.get("relays", 0),
                "temperature": server_state.get("temperature", 0),
                "humidity": server_state.get("humidity", 0),
                "door": server_state.get("door", "unknown"),
                "lock": server_state.get("lock", "unknown"),
                "motion": server_state.get("motion", False),
                "voltage": server_state.get("voltage", 0),
                "schedules": server_state.get("schedules", 0),
            },
            "camera": {
                "online": cam_state.get("device") is not None,
                "streaming": cam_state.get("streaming", False),
                "fps": cam_state.get("fps", 0),
                "night_mode": cam_state.get("night_mode", False),
                "patrol": cam_state.get("patrol", False),
                "intruder_mode": cam_state.get("intruder_mode", False),
                "persons": cam_state.get("persons", 0),
                "captures": cam_state.get("captures", 0),
                "detections": cam_state.get("detections", 0),
            }
        }
