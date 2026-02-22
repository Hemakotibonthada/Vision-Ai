"""
Jarvis AI - State Machine / Brain
====================================
The core intelligence that orchestrates all Jarvis services.
Manages state transitions, event handling, and the main AI loop.
"""
import asyncio
import time
import json
import os
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Callable, Any

from loguru import logger

from jarvis.config import settings
from jarvis.services.face_recognition_service import face_service
from jarvis.services.voice_service import voice_service
from jarvis.services.camera_service import camera_service
from jarvis.services.room_presence_service import presence_service, PresenceState
from jarvis.services.home_automation_service import home_service


class JarvisState(str, Enum):
    INITIALIZING = "initializing"
    SLEEPING = "sleeping"          # Room empty — low power, learning mode
    WATCHING = "watching"          # Passive monitoring, no owner
    OWNER_PRESENT = "owner_present"  # Owner detected, ready
    LISTENING = "listening"        # Actively listening for voice commands
    EXECUTING = "executing"        # Processing a command
    INTRUDER_ALERT = "intruder_alert"  # Unknown person detected
    LEARNING = "learning"          # Studying patterns


class JarvisBrain:
    """Core state machine that drives Jarvis."""

    def __init__(self):
        self._state = JarvisState.INITIALIZING
        self._previous_state = JarvisState.INITIALIZING
        self._state_enter_time = time.time()
        self._running = False
        self._main_task: Optional[asyncio.Task] = None

        # Event log
        self._event_log: list = []
        self._max_log = 500

        # Conversation context
        self._last_command = ""
        self._last_response = ""
        self._conversation_active = False

        # Stats
        self._stats = {
            "started_at": None,
            "owner_greetings": 0,
            "intruder_alerts": 0,
            "commands_processed": 0,
            "state_changes": 0,
            "uptime_seconds": 0,
        }

        # External callbacks (for WebSocket push etc.)
        self._state_change_callbacks: list = []

        logger.info("Jarvis Brain initialized")

    # ================================================================
    # Properties
    # ================================================================
    @property
    def state(self) -> JarvisState:
        return self._state

    @property
    def state_info(self) -> Dict:
        return {
            "state": self._state.value,
            "previous_state": self._previous_state.value,
            "state_duration": time.time() - self._state_enter_time,
            "running": self._running,
            "stats": self._stats,
        }

    # ================================================================
    # State Transitions
    # ================================================================
    async def _transition(self, new_state: JarvisState, reason: str = ""):
        """Transition to a new state."""
        if new_state == self._state:
            return

        old = self._state
        self._previous_state = old
        self._state = new_state
        self._state_enter_time = time.time()
        self._stats["state_changes"] += 1

        self._log_event("state_change", {
            "from": old.value,
            "to": new_state.value,
            "reason": reason,
        })

        logger.info(f"State: {old.value} → {new_state.value} ({reason})")

        # Execute state entry actions
        await self._on_state_enter(new_state, old)

        # Notify external listeners
        for cb in self._state_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(old.value, new_state.value, reason)
                else:
                    cb(old.value, new_state.value, reason)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

    async def _on_state_enter(self, new_state: JarvisState, old_state: JarvisState):
        """Execute actions when entering a new state."""

        if new_state == JarvisState.SLEEPING:
            voice_service.announce_sleep_mode()
            logger.info("Jarvis entering sleep mode — room is empty")

        elif new_state == JarvisState.WATCHING:
            logger.info("Jarvis watching — passive monitoring active")

        elif new_state == JarvisState.OWNER_PRESENT:
            self._stats["owner_greetings"] += 1
            logger.info("Owner detected — Jarvis is ready")

        elif new_state == JarvisState.LISTENING:
            logger.info("Jarvis listening for commands...")

        elif new_state == JarvisState.INTRUDER_ALERT:
            self._stats["intruder_alerts"] += 1
            voice_service.announce_intruder()
            # Trigger buzzer on ESP32
            try:
                await home_service.buzz("alert")
            except Exception:
                pass
            logger.warning("INTRUDER ALERT — recording & alerting")

        elif new_state == JarvisState.LEARNING:
            logger.info("Jarvis in learning mode — analyzing patterns")

    # ================================================================
    # Lifecycle
    # ================================================================
    async def start(self):
        """Start the Jarvis brain and all services."""
        if self._running:
            return

        logger.info("=" * 60)
        logger.info("  JARVIS AI SYSTEM STARTING")
        logger.info("=" * 60)

        self._running = True
        self._stats["started_at"] = datetime.now().isoformat()

        # Initialize camera
        camera_service.start()
        await asyncio.sleep(1)  # Give camera time to warm up

        # Register presence callbacks
        presence_service.on("owner_entered", self._handle_owner_entered)
        presence_service.on("owner_left", self._handle_owner_left)
        presence_service.on("intruder_detected", self._handle_intruder_detected)
        presence_service.on("room_empty", self._handle_room_empty)

        # Start presence monitoring
        await presence_service.start_monitoring()

        # Transition to watching
        await self._transition(JarvisState.WATCHING, "System started")

        # Start main loop
        self._main_task = asyncio.create_task(self._main_loop())

        voice_service.speak("Jarvis system online. All sensors active. Ready to serve.")
        logger.info("Jarvis AI system fully started")

    async def stop(self):
        """Stop the Jarvis brain and all services."""
        logger.info("Jarvis AI system shutting down...")
        self._running = False

        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass

        await presence_service.stop_monitoring()
        camera_service.stop()
        voice_service.speak("Jarvis system going offline. Goodbye.")
        await asyncio.sleep(2)

        logger.info("Jarvis AI system stopped")

    # ================================================================
    # Main Loop
    # ================================================================
    async def _main_loop(self):
        """Main AI loop — runs continuously, managing state behavior."""
        while self._running:
            try:
                self._stats["uptime_seconds"] = (
                    time.time() - time.mktime(
                        datetime.fromisoformat(self._stats["started_at"]).timetuple()
                    )
                ) if self._stats["started_at"] else 0

                current = self._state
                duration = time.time() - self._state_enter_time

                # ---- State-specific behavior ----
                if current == JarvisState.SLEEPING:
                    await self._sleeping_behavior(duration)

                elif current == JarvisState.WATCHING:
                    await self._watching_behavior(duration)

                elif current == JarvisState.OWNER_PRESENT:
                    await self._owner_present_behavior(duration)

                elif current == JarvisState.LISTENING:
                    await self._listening_behavior(duration)

                elif current == JarvisState.INTRUDER_ALERT:
                    await self._intruder_alert_behavior(duration)

                elif current == JarvisState.LEARNING:
                    await self._learning_behavior(duration)

                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(2)

    # ================================================================
    # State Behaviors
    # ================================================================
    async def _sleeping_behavior(self, duration: float):
        """Behavior while sleeping — minimal activity, periodic learning."""
        # Periodically enter learning mode
        if duration > 300:  # Every 5 minutes
            await self._transition(JarvisState.LEARNING, "Periodic learning cycle")

    async def _watching_behavior(self, duration: float):
        """Passive watching — wait for presence changes."""
        # If nobody for a long time, go to sleep
        if duration > settings.IDLE_TIMEOUT_SECONDS:
            await self._transition(JarvisState.SLEEPING, "Room idle timeout")

    async def _owner_present_behavior(self, duration: float):
        """Owner is present — be ready for commands."""
        # After a while without interaction, offer help or go quiet
        pass

    async def _listening_behavior(self, duration: float):
        """Actively listening for voice commands."""
        # Timeout listening after 30 seconds
        if duration > 30:
            await self._transition(JarvisState.OWNER_PRESENT, "Listening timeout")

    async def _intruder_alert_behavior(self, duration: float):
        """Intruder detected — keep alerting and recording."""
        # Check if intruder is still present
        state = presence_service.get_state()
        if state["presence"] == PresenceState.EMPTY.value:
            await self._transition(JarvisState.WATCHING, "Intruder left")
        elif state["presence"] == PresenceState.OWNER_PRESENT.value:
            await self._transition(JarvisState.OWNER_PRESENT, "Owner returned during alert")

        # Re-alert every 60 seconds
        if duration > 0 and int(duration) % 60 == 0:
            voice_service.announce_intruder()

    async def _learning_behavior(self, duration: float):
        """Learning mode — analyze patterns, optimize behavior."""
        # Learning cycle is short, then go back to sleep or watching
        if duration > 30:
            room_state = presence_service.get_state()
            if room_state["presence"] == PresenceState.EMPTY.value:
                await self._transition(JarvisState.SLEEPING, "Learning complete, room empty")
            else:
                await self._transition(JarvisState.WATCHING, "Learning complete")

    # ================================================================
    # Event Handlers (from presence service)
    # ================================================================
    async def _handle_owner_entered(self, data):
        """Handle owner entering the room."""
        name = data.get("name", settings.OWNER_NAME)
        should_greet = data.get("should_greet", True)

        if should_greet:
            voice_service.greet_owner(name)

        await self._transition(JarvisState.OWNER_PRESENT, f"Owner {name} entered")

    async def _handle_owner_left(self, data):
        """Handle owner leaving."""
        if self._state == JarvisState.OWNER_PRESENT:
            await self._transition(JarvisState.WATCHING, "Owner left the room")

    async def _handle_intruder_detected(self, data):
        """Handle intruder detection."""
        await self._transition(JarvisState.INTRUDER_ALERT, "Unknown person detected")

    async def _handle_room_empty(self, data):
        """Handle room becoming empty."""
        if self._state != JarvisState.SLEEPING:
            await self._transition(JarvisState.WATCHING, "Room empty")

    # ================================================================
    # Command Interface
    # ================================================================
    async def process_voice_command(self, command: str) -> str:
        """Process a voice command and return response."""
        self._last_command = command
        self._stats["commands_processed"] += 1
        self._log_event("command", {"text": command})

        command_lower = command.lower().strip()

        # ---- Jarvis meta commands ----
        if any(w in command_lower for w in ["status", "how are you", "system status"]):
            response = self._get_status_report()

        elif any(w in command_lower for w in ["sleep", "go to sleep", "goodnight"]):
            await self._transition(JarvisState.SLEEPING, "User commanded sleep")
            response = "Going to sleep mode. Goodnight!"

        elif any(w in command_lower for w in ["wake up", "wake", "good morning"]):
            await self._transition(JarvisState.OWNER_PRESENT, "User woke Jarvis")
            response = "I'm awake and ready!"

        elif any(w in command_lower for w in ["who am i", "identify me"]):
            frame = camera_service.get_latest_frame()
            if frame is not None:
                results = face_service.recognize_faces(frame)
                if results:
                    names = [r.get("name", "Unknown") for r in results]
                    response = f"I see: {', '.join(names)}"
                else:
                    response = "I can't see anyone clearly right now."
            else:
                response = "Camera is not available."

        elif any(w in command_lower for w in ["intruders", "security", "who came"]):
            count = presence_service.get_intruder_count()
            if count == 0:
                response = "No intruders detected today."
            else:
                records = presence_service.get_intruder_records()
                response = f"{count} intruder event(s) recorded. Last at {records[-1]['timestamp']}."

        elif any(w in command_lower for w in ["register", "learn my face", "remember me"]):
            frame = camera_service.get_latest_frame()
            if frame is not None:
                success = face_service.register_owner(settings.OWNER_NAME, frame)
                if success:
                    response = f"Face registered successfully as {settings.OWNER_NAME}."
                else:
                    response = "Could not detect a face. Please look at the camera."
            else:
                response = "Camera is not available."

        # ---- Home automation commands ----
        elif any(w in command_lower for w in [
            "light", "relay", "switch", "turn on", "turn off",
            "temperature", "humidity", "sensor", "power", "voltage",
            "all on", "all off", "scene", "alarm", "buzz"
        ]):
            response = await home_service.process_command(command)

        # ---- Conversational ----
        elif any(w in command_lower for w in ["hello", "hi", "hey"]):
            response = f"Hello {settings.OWNER_NAME}! How can I assist you?"

        elif any(w in command_lower for w in ["thank", "thanks"]):
            response = "You're welcome! Always here to help."

        elif any(w in command_lower for w in ["bye", "goodbye", "see you"]):
            response = f"Goodbye {settings.OWNER_NAME}! I'll keep watching over things."

        elif "time" in command_lower:
            now = datetime.now().strftime("%I:%M %p")
            response = f"The current time is {now}."

        elif "date" in command_lower:
            today = datetime.now().strftime("%A, %B %d, %Y")
            response = f"Today is {today}."

        else:
            response = f"I heard: '{command}'. I'm not sure how to handle that yet."

        self._last_response = response
        self._log_event("response", {"text": response})
        voice_service.speak(response)
        return response

    def _get_status_report(self) -> str:
        """Generate a spoken status report."""
        room = presence_service.get_state()
        parts = [f"System is {self._state.value}."]

        if room["owner_detected"]:
            parts.append(f"Welcome, {room['owner_name'] or settings.OWNER_NAME}.")

        parts.append(f"Room has {room['num_faces']} person(s) detected.")
        parts.append(f"Commands processed: {self._stats['commands_processed']}.")
        parts.append(f"Intruder events: {self._stats['intruder_alerts']}.")

        uptime_m = int(self._stats["uptime_seconds"] / 60)
        parts.append(f"Uptime: {uptime_m} minutes.")

        return " ".join(parts)

    # ================================================================
    # Logging
    # ================================================================
    def _log_event(self, event_type: str, data: Dict):
        entry = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "state": self._state.value,
            "data": data,
        }
        self._event_log.append(entry)
        if len(self._event_log) > self._max_log:
            self._event_log = self._event_log[-self._max_log:]

    def get_event_log(self, limit: int = 50) -> list:
        return self._event_log[-limit:]

    def on_state_change(self, callback):
        """Register a state-change callback."""
        self._state_change_callbacks.append(callback)


# Singleton
jarvis_brain = JarvisBrain()
