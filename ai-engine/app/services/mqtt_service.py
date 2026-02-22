"""
Vision-AI MQTT Service
Features: MQTT client for device communication
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Callable, Optional
from loguru import logger

import paho.mqtt.client as mqtt_client

from app.config import settings


class MQTTService:
    """MQTT client for ESP32 device communication."""

    def __init__(self):
        self.client = mqtt_client.Client(client_id=settings.MQTT_CLIENT_ID)
        self.connected = False
        self.message_count = 0
        self.callbacks = {}
        self.message_history = []

    def connect(self):
        """Connect to MQTT broker."""
        self.client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        try:
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=60)
            self.client.loop_start()
            logger.info(f"MQTT connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected!")

            # Subscribe to all vision-ai topics
            prefix = settings.MQTT_TOPIC_PREFIX
            self.client.subscribe(f"{prefix}#")
            logger.info(f"Subscribed to {prefix}#")
        else:
            logger.error(f"MQTT connection failed: {rc}")

    def _on_message(self, client, userdata, msg):
        self.message_count += 1
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = msg.payload.decode()

        self.message_history.append({
            "topic": topic,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep last 200 messages
        if len(self.message_history) > 200:
            self.message_history = self.message_history[-200:]

        # Route to registered callbacks
        for pattern, callback in self.callbacks.items():
            if topic.startswith(pattern) or pattern == topic:
                try:
                    callback(topic, payload)
                except Exception as e:
                    logger.error(f"Callback error for {topic}: {e}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.warning(f"MQTT disconnected: {rc}")

    def subscribe(self, topic: str, callback: Callable = None):
        self.client.subscribe(topic)
        if callback:
            self.callbacks[topic] = callback

    def publish(self, topic: str, payload: Dict, retain: bool = False):
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        self.client.publish(topic, payload, retain=retain)

    def register_callback(self, topic_pattern: str, callback: Callable):
        self.callbacks[topic_pattern] = callback

    def get_status(self) -> Dict:
        return {
            "connected": self.connected,
            "broker": settings.MQTT_BROKER,
            "port": settings.MQTT_PORT,
            "message_count": self.message_count,
            "subscriptions": list(self.callbacks.keys()),
            "recent_messages": len(self.message_history)
        }

    def get_recent_messages(self, limit: int = 50) -> list:
        return self.message_history[-limit:]

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


# Singleton
mqtt_service = MQTTService()
