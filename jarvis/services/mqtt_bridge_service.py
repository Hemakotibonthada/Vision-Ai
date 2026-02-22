"""
Vision-AI MQTT Bridge Service v3.0
Bridges MQTT messages between ESP32 devices and Jarvis AI brain.
Subscribes to all Jarvis topics, routes events, manages device state.
"""

import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass, field

try:
    import paho.mqtt.client as mqtt_client
except ImportError:
    mqtt_client = None

logger = logging.getLogger("jarvis.mqtt_bridge")


@dataclass
class DeviceState:
    """Tracks the state of a connected ESP32 device."""
    device_id: str
    device_type: str = "unknown"  # "server" or "camera"
    ip: str = ""
    firmware: str = ""
    online: bool = False
    last_heartbeat: float = 0.0
    uptime: int = 0
    rssi: int = 0
    free_heap: int = 0
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_stale(self) -> bool:
        return time.time() - self.last_heartbeat > 45  # 3 missed heartbeats


class MQTTBridgeService:
    """
    Central MQTT bridge for Vision-AI system.
    Connects to the MQTT broker, subscribes to all Jarvis topics,
    and routes events to the appropriate Jarvis services.
    """

    # MQTT Topics
    TOPIC_PREFIX = "vision-ai/"

    # Server topics
    TOPIC_JARVIS_CMD      = TOPIC_PREFIX + "jarvis/cmd"
    TOPIC_JARVIS_STATE    = TOPIC_PREFIX + "jarvis/state"
    TOPIC_JARVIS_EVENT    = TOPIC_PREFIX + "jarvis/event"
    TOPIC_JARVIS_DOOR     = TOPIC_PREFIX + "jarvis/door"
    TOPIC_JARVIS_MOTION   = TOPIC_PREFIX + "jarvis/motion"
    TOPIC_JARVIS_RELAY    = TOPIC_PREFIX + "jarvis/relay"
    TOPIC_JARVIS_SENSOR   = TOPIC_PREFIX + "jarvis/sensor"
    TOPIC_JARVIS_ALERT    = TOPIC_PREFIX + "jarvis/alert"
    TOPIC_JARVIS_LOCK     = TOPIC_PREFIX + "jarvis/lock"
    TOPIC_JARVIS_SCHED    = TOPIC_PREFIX + "jarvis/schedule"
    TOPIC_JARVIS_HEARTBEAT = TOPIC_PREFIX + "jarvis/heartbeat"

    # Camera topics
    TOPIC_CAM_STATUS      = TOPIC_PREFIX + "camera/status"
    TOPIC_CAM_MOTION      = TOPIC_PREFIX + "camera/motion"
    TOPIC_CAM_FACE        = TOPIC_PREFIX + "camera/face"
    TOPIC_JARVIS_CAM_EVENT = TOPIC_PREFIX + "jarvis/camera/event"
    TOPIC_JARVIS_CAM_PERSON = TOPIC_PREFIX + "jarvis/camera/person"
    TOPIC_JARVIS_CAM_ALERT = TOPIC_PREFIX + "jarvis/camera/alert"
    TOPIC_JARVIS_CAM_HEARTBEAT = TOPIC_PREFIX + "jarvis/camera/heartbeat"
    TOPIC_JARVIS_INTRUDER = TOPIC_PREFIX + "jarvis/intruder"
    TOPIC_JARVIS_FACE_ID  = TOPIC_PREFIX + "jarvis/face/identified"
    TOPIC_JARVIS_PATROL   = TOPIC_PREFIX + "jarvis/patrol"
    TOPIC_AI_INFERENCE    = TOPIC_PREFIX + "ai/inference"

    def __init__(self, broker: str = "127.0.0.1", port: int = 1883,
                 username: str = "", password: str = "",
                 client_id: str = "jarvis-bridge"):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id

        self.client: Optional[mqtt_client.Client] = None
        self.connected = False
        self.devices: Dict[str, DeviceState] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._message_log: List[Dict] = []
        self._max_log_size = 500

        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "events_routed": 0,
            "reconnections": 0,
            "errors": 0,
            "start_time": time.time()
        }

    def register_handler(self, event_type: str, handler: Callable):
        """Register a callback for a specific event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event: {event_type}")

    def _fire_event(self, event_type: str, data: Dict):
        """Fire registered event handlers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.get_event_loop().create_task(handler(data))
                else:
                    handler(data)
                self.stats["events_routed"] += 1
            except Exception as e:
                logger.error(f"Event handler error ({event_type}): {e}")
                self.stats["errors"] += 1

    def connect(self) -> bool:
        """Connect to the MQTT broker."""
        if mqtt_client is None:
            logger.error("paho-mqtt not installed. Run: pip install paho-mqtt")
            return False

        try:
            self.client = mqtt_client.Client(client_id=self.client_id)

            if self.username:
                self.client.username_pw_set(self.username, self.password)

            # Set LWT (Last Will and Testament)
            lwt_payload = json.dumps({
                "service": "jarvis-bridge",
                "status": "offline",
                "timestamp": time.time()
            })
            self.client.will_set(
                self.TOPIC_JARVIS_STATE,
                payload=lwt_payload,
                qos=1,
                retain=True
            )

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            return True

        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            self.stats["errors"] += 1
            return False

    def disconnect(self):
        """Disconnect from the MQTT broker."""
        if self.client:
            # Publish offline status
            self.publish(self.TOPIC_JARVIS_STATE, {
                "service": "jarvis-bridge",
                "status": "offline",
                "timestamp": time.time()
            })
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT broker")

    def _on_connect(self, client, userdata, flags, rc):
        """Handle successful MQTT connection."""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")

            # Subscribe to all Jarvis topics
            subscriptions = [
                (self.TOPIC_JARVIS_EVENT, 1),
                (self.TOPIC_JARVIS_DOOR, 1),
                (self.TOPIC_JARVIS_MOTION, 1),
                (self.TOPIC_JARVIS_RELAY, 1),
                (self.TOPIC_JARVIS_SENSOR, 1),
                (self.TOPIC_JARVIS_ALERT, 1),
                (self.TOPIC_JARVIS_LOCK, 1),
                (self.TOPIC_JARVIS_SCHED, 1),
                (self.TOPIC_JARVIS_HEARTBEAT, 1),
                (self.TOPIC_CAM_STATUS, 1),
                (self.TOPIC_CAM_MOTION, 1),
                (self.TOPIC_CAM_FACE, 1),
                (self.TOPIC_JARVIS_CAM_EVENT, 1),
                (self.TOPIC_JARVIS_CAM_PERSON, 1),
                (self.TOPIC_JARVIS_CAM_ALERT, 1),
                (self.TOPIC_JARVIS_CAM_HEARTBEAT, 1),
                (self.TOPIC_JARVIS_INTRUDER, 1),
                (self.TOPIC_JARVIS_FACE_ID, 1),
                (self.TOPIC_JARVIS_PATROL, 1),
                (self.TOPIC_AI_INFERENCE, 0),
            ]
            client.subscribe(subscriptions)
            logger.info(f"Subscribed to {len(subscriptions)} topics")

            # Announce online
            self.publish(self.TOPIC_JARVIS_STATE, {
                "service": "jarvis-bridge",
                "status": "online",
                "timestamp": time.time(),
                "subscriptions": len(subscriptions)
            })
        else:
            logger.error(f"MQTT connection failed with code: {rc}")
            self.stats["errors"] += 1

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect (rc={rc}), will auto-reconnect")
            self.stats["reconnections"] += 1

    def _on_message(self, client, userdata, msg):
        """Route incoming MQTT messages to appropriate handlers."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8", errors="replace")
            self.stats["messages_received"] += 1

            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = {"raw": payload}

            # Log message
            log_entry = {
                "topic": topic,
                "data": data,
                "timestamp": time.time()
            }
            self._message_log.append(log_entry)
            if len(self._message_log) > self._max_log_size:
                self._message_log = self._message_log[-self._max_log_size:]

            # Route by topic
            if topic == self.TOPIC_JARVIS_HEARTBEAT:
                self._handle_server_heartbeat(data)
            elif topic == self.TOPIC_JARVIS_CAM_HEARTBEAT:
                self._handle_cam_heartbeat(data)
            elif topic == self.TOPIC_JARVIS_DOOR:
                self._handle_door_event(data)
            elif topic == self.TOPIC_JARVIS_INTRUDER:
                self._handle_intruder_alert(data)
            elif topic == self.TOPIC_JARVIS_CAM_PERSON:
                self._handle_person_detection(data)
            elif topic == self.TOPIC_JARVIS_FACE_ID:
                self._handle_face_identified(data)
            elif topic == self.TOPIC_JARVIS_ALERT:
                self._handle_alert(data)
            elif topic == self.TOPIC_JARVIS_LOCK:
                self._handle_lock_event(data)
            elif topic in (self.TOPIC_JARVIS_MOTION, self.TOPIC_CAM_MOTION):
                self._handle_motion_event(data)
            elif topic == self.TOPIC_JARVIS_RELAY:
                self._handle_relay_event(data)
            elif topic == self.TOPIC_JARVIS_SENSOR:
                self._handle_sensor_data(data)
            elif topic == self.TOPIC_JARVIS_PATROL:
                self._handle_patrol_event(data)
            elif topic == self.TOPIC_JARVIS_EVENT:
                self._handle_generic_event(data)
            elif topic == self.TOPIC_AI_INFERENCE:
                self._handle_ai_inference(data)
            elif topic == self.TOPIC_CAM_STATUS:
                self._handle_cam_status(data)

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
            self.stats["errors"] += 1

    # ---- Event Handlers ----

    def _handle_server_heartbeat(self, data: Dict):
        device_id = data.get("device", "esp32-server")
        if device_id not in self.devices:
            self.devices[device_id] = DeviceState(device_id=device_id, device_type="server")
        dev = self.devices[device_id]
        dev.online = True
        dev.last_heartbeat = time.time()
        dev.ip = data.get("ip", dev.ip)
        dev.firmware = data.get("firmware", dev.firmware)
        dev.uptime = data.get("uptime", 0)
        dev.rssi = data.get("rssi", 0)
        dev.free_heap = data.get("free_heap", 0)
        dev.data = data
        self._fire_event("heartbeat", {"source": "server", **data})

    def _handle_cam_heartbeat(self, data: Dict):
        device_id = data.get("device", "esp32-cam")
        if device_id not in self.devices:
            self.devices[device_id] = DeviceState(device_id=device_id, device_type="camera")
        dev = self.devices[device_id]
        dev.online = True
        dev.last_heartbeat = time.time()
        dev.ip = data.get("ip", dev.ip)
        dev.firmware = data.get("firmware", dev.firmware)
        dev.uptime = data.get("uptime", 0)
        dev.rssi = data.get("rssi", 0)
        dev.free_heap = data.get("free_heap", 0)
        dev.data = data
        self._fire_event("heartbeat", {"source": "camera", **data})

    def _handle_door_event(self, data: Dict):
        logger.info(f"Door event: {data.get('state', 'unknown')}")
        self._fire_event("door", data)

    def _handle_intruder_alert(self, data: Dict):
        logger.warning(f"INTRUDER ALERT: {data.get('reason', 'unknown')}")
        self._fire_event("intruder", data)

    def _handle_person_detection(self, data: Dict):
        count = data.get("count", data.get("persons", 0))
        logger.info(f"Person detection: {count} person(s)")
        self._fire_event("person_detected", data)

    def _handle_face_identified(self, data: Dict):
        faces = data.get("faces", [])
        names = [f.get("name", "unknown") for f in faces]
        logger.info(f"Face identified: {names}")
        self._fire_event("face_identified", data)

    def _handle_alert(self, data: Dict):
        logger.warning(f"Alert: {data}")
        self._fire_event("alert", data)

    def _handle_lock_event(self, data: Dict):
        logger.info(f"Lock event: {data.get('state', 'unknown')}")
        self._fire_event("lock", data)

    def _handle_motion_event(self, data: Dict):
        self._fire_event("motion", data)

    def _handle_relay_event(self, data: Dict):
        self._fire_event("relay", data)

    def _handle_sensor_data(self, data: Dict):
        self._fire_event("sensor", data)

    def _handle_patrol_event(self, data: Dict):
        self._fire_event("patrol", data)

    def _handle_generic_event(self, data: Dict):
        event_type = data.get("event", "unknown")
        self._fire_event(event_type, data)

    def _handle_ai_inference(self, data: Dict):
        self._fire_event("ai_inference", data)

    def _handle_cam_status(self, data: Dict):
        device_id = data.get("camera", "esp32-cam")
        if device_id not in self.devices:
            self.devices[device_id] = DeviceState(device_id=device_id, device_type="camera")
        dev = self.devices[device_id]
        dev.online = data.get("status") == "online"
        dev.ip = data.get("ip", dev.ip)
        dev.firmware = data.get("firmware", dev.firmware)
        dev.data.update(data)

    # ---- Command Publishing ----

    def publish(self, topic: str, data: Any, qos: int = 1, retain: bool = False) -> bool:
        """Publish a message to an MQTT topic."""
        if not self.client or not self.connected:
            logger.warning("Cannot publish: not connected")
            return False

        try:
            if isinstance(data, dict):
                payload = json.dumps(data)
            elif isinstance(data, str):
                payload = data
            else:
                payload = str(data)

            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            self.stats["messages_sent"] += 1
            return result.rc == mqtt_client.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error(f"Publish error: {e}")
            self.stats["errors"] += 1
            return False

    def send_command(self, command: str, params: Dict = None) -> bool:
        """Send a command to the ESP32 server via MQTT."""
        data = {"command": command}
        if params:
            data.update(params)
        return self.publish(self.TOPIC_JARVIS_CMD, data)

    def send_camera_command(self, command: str, params: Dict = None) -> bool:
        """Send a command to the ESP32-CAM via MQTT."""
        data = {"command": command}
        if params:
            data.update(params)
        return self.publish(self.TOPIC_PREFIX + "jarvis/camera/cmd", data)

    # ---- Convenience Methods ----

    def set_relay(self, relay_id: int, state: bool) -> bool:
        return self.send_command("relay", {"relay": relay_id, "state": 1 if state else 0})

    def set_lock(self, locked: bool) -> bool:
        return self.send_command("lock" if locked else "unlock")

    def trigger_capture(self, context: str = "jarvis") -> bool:
        return self.send_camera_command("capture", {"context": context})

    def start_patrol(self) -> bool:
        return self.send_camera_command("patrol_start")

    def stop_patrol(self) -> bool:
        return self.send_camera_command("patrol_stop")

    def set_intruder_mode(self, enabled: bool) -> bool:
        return self.send_camera_command("intruder_mode", {"enabled": enabled})

    def trigger_burst(self) -> bool:
        return self.send_camera_command("burst")

    def set_flash(self, intensity: int) -> bool:
        return self.send_camera_command("flash", {"intensity": intensity})

    def request_identify(self) -> bool:
        return self.send_camera_command("identify")

    def activate_scene(self, scene_name: str) -> bool:
        return self.send_command("scene", {"name": scene_name})

    def buzz_alert(self, pattern: str = "alert") -> bool:
        return self.send_command("buzz", {"pattern": pattern})

    # ---- State Queries ----

    def get_device_state(self, device_id: str) -> Optional[Dict]:
        dev = self.devices.get(device_id)
        if dev:
            return {
                "device_id": dev.device_id,
                "type": dev.device_type,
                "online": dev.online and not dev.is_stale,
                "ip": dev.ip,
                "firmware": dev.firmware,
                "uptime": dev.uptime,
                "rssi": dev.rssi,
                "free_heap": dev.free_heap,
                "last_heartbeat": dev.last_heartbeat,
                "data": dev.data
            }
        return None

    def get_all_devices(self) -> Dict[str, Dict]:
        result = {}
        for dev_id, dev in self.devices.items():
            result[dev_id] = {
                "device_id": dev.device_id,
                "type": dev.device_type,
                "online": dev.online and not dev.is_stale,
                "ip": dev.ip,
                "firmware": dev.firmware,
                "last_heartbeat": dev.last_heartbeat,
                "uptime": dev.uptime
            }
        return result

    def get_recent_messages(self, count: int = 50, topic_filter: str = None) -> List[Dict]:
        msgs = self._message_log
        if topic_filter:
            msgs = [m for m in msgs if topic_filter in m["topic"]]
        return msgs[-count:]

    def get_stats(self) -> Dict:
        runtime = time.time() - self.stats["start_time"]
        return {
            **self.stats,
            "runtime_seconds": int(runtime),
            "connected": self.connected,
            "devices_online": sum(1 for d in self.devices.values() if d.online and not d.is_stale),
            "devices_total": len(self.devices)
        }
