"""
Jarvis AI - Voice Service (Text-to-Speech & Speech-to-Text)
=============================================================
Handles speaking (TTS) and listening (STT) for Jarvis.
Supports offline operation via pyttsx3/vosk.
"""
import os
import time
import queue
import threading
import json
from datetime import datetime
from typing import Optional, Callable
from loguru import logger

from jarvis.config import settings

# ---- TTS Engine ----
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

# ---- STT Engine ----
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    from vosk import Model as VoskModel, KaldiRecognizer
    import pyaudio
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False


class VoiceService:
    """Handles Jarvis voice input/output."""

    def __init__(self):
        self._tts_engine = None
        self._tts_lock = threading.Lock()
        self._recognizer = None
        self._vosk_model = None
        self._listening = False
        self._speak_queue = queue.Queue()
        self._speak_thread = None
        self._command_callback: Optional[Callable] = None
        self._last_spoken = ""
        self._conversation_log = []

        self._init_tts()
        self._init_stt()
        self._start_speak_thread()

        logger.info("Voice service initialized")

    # ================================================================
    # Text-to-Speech
    # ================================================================
    def _init_tts(self):
        """Initialize TTS engine."""
        if PYTTSX3_AVAILABLE:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", settings.TTS_RATE)
                self._tts_engine.setProperty("volume", settings.TTS_VOLUME)

                # Try to set a good voice
                voices = self._tts_engine.getProperty("voices")
                for voice in voices:
                    if "english" in voice.name.lower() or "david" in voice.name.lower():
                        self._tts_engine.setProperty("voice", voice.id)
                        break

                logger.info("pyttsx3 TTS engine initialized")
            except Exception as e:
                logger.warning(f"pyttsx3 init failed: {e}")
                self._tts_engine = None
        else:
            logger.warning("pyttsx3 not available. TTS disabled.")

    def _start_speak_thread(self):
        """Background thread for speaking without blocking."""
        def worker():
            while True:
                try:
                    text = self._speak_queue.get(timeout=1)
                    if text is None:
                        break
                    self._do_speak(text)
                    self._speak_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Speak thread error: {e}")

        self._speak_thread = threading.Thread(target=worker, daemon=True)
        self._speak_thread.start()

    def speak(self, text: str, block: bool = False):
        """Speak text. Non-blocking by default."""
        self._last_spoken = text
        self._conversation_log.append({
            "role": "jarvis",
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"[Jarvis] {text}")

        if block:
            self._do_speak(text)
        else:
            self._speak_queue.put(text)

    def _do_speak(self, text: str):
        """Actually speak the text."""
        if self._tts_engine:
            with self._tts_lock:
                try:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                except Exception as e:
                    logger.error(f"TTS error: {e}")
                    # Reinitialize engine
                    try:
                        self._tts_engine = pyttsx3.init()
                        self._tts_engine.setProperty("rate", settings.TTS_RATE)
                        self._tts_engine.setProperty("volume", settings.TTS_VOLUME)
                        self._tts_engine.say(text)
                        self._tts_engine.runAndWait()
                    except Exception:
                        pass

    # ================================================================
    # Speech-to-Text
    # ================================================================
    def _init_stt(self):
        """Initialize speech recognition."""
        if SR_AVAILABLE:
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = settings.ENERGY_THRESHOLD
            self._recognizer.dynamic_energy_threshold = True
            logger.info("SpeechRecognition STT initialized")

        if VOSK_AVAILABLE and os.path.exists(settings.VOSK_MODEL_PATH):
            try:
                self._vosk_model = VoskModel(settings.VOSK_MODEL_PATH)
                logger.info("Vosk offline model loaded")
            except Exception as e:
                logger.warning(f"Vosk model load failed: {e}")

    def listen(self, timeout: int = None) -> Optional[str]:
        """Listen for a voice command. Returns transcribed text or None."""
        timeout = timeout or settings.LISTEN_TIMEOUT

        if SR_AVAILABLE and self._recognizer:
            return self._listen_sr(timeout)
        elif VOSK_AVAILABLE and self._vosk_model:
            return self._listen_vosk(timeout)
        else:
            logger.warning("No STT engine available")
            return None

    def _listen_sr(self, timeout: int) -> Optional[str]:
        """Listen using SpeechRecognition library."""
        try:
            with sr.Microphone() as source:
                logger.debug("Listening...")
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self._recognizer.listen(
                    source, timeout=timeout,
                    phrase_time_limit=settings.PHRASE_TIMEOUT
                )

            # Try Google first (online), fallback to Sphinx (offline)
            try:
                text = self._recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                return None
            except sr.RequestError:
                # Offline fallback
                try:
                    text = self._recognizer.recognize_sphinx(audio)
                except Exception:
                    return None

            text = text.strip().lower()
            if text:
                self._conversation_log.append({
                    "role": "user",
                    "text": text,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"[User] {text}")
            return text

        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            logger.error(f"Listen error: {e}")
            return None

    def _listen_vosk(self, timeout: int) -> Optional[str]:
        """Listen using Vosk offline model."""
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1,
                          rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()

            rec = KaldiRecognizer(self._vosk_model, 16000)
            start_time = time.time()

            while time.time() - start_time < timeout:
                data = stream.read(4000, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        stream.stop_stream()
                        stream.close()
                        p.terminate()
                        self._conversation_log.append({
                            "role": "user", "text": text,
                            "timestamp": datetime.now().isoformat()
                        })
                        return text

            # Get final partial result
            result = json.loads(rec.FinalResult())
            text = result.get("text", "").strip()

            stream.stop_stream()
            stream.close()
            p.terminate()
            return text if text else None

        except Exception as e:
            logger.error(f"Vosk listen error: {e}")
            return None

    def listen_for_wake_word(self, timeout: int = 30) -> bool:
        """Listen specifically for the wake word."""
        text = self.listen(timeout)
        if text and settings.WAKE_WORD.lower() in text.lower():
            return True
        return False

    # ================================================================
    # Greetings & Responses
    # ================================================================
    def greet_owner(self, owner_name: str = None, time_of_day: str = None):
        """Generate and speak a greeting for the owner."""
        name = owner_name or settings.OWNER_NAME
        if not time_of_day:
            hour = datetime.now().hour
            if hour < 12:
                time_of_day = "morning"
            elif hour < 17:
                time_of_day = "afternoon"
            else:
                time_of_day = "evening"

        greetings = {
            "morning": [
                f"Good morning, {name}. I hope you had a restful night.",
                f"Good morning, {name}. Ready to start the day?",
                f"Rise and shine, {name}. The systems are all operational.",
            ],
            "afternoon": [
                f"Good afternoon, {name}. Welcome back.",
                f"Hello, {name}. Good to see you this afternoon.",
                f"Welcome back, {name}. How can I assist you?",
            ],
            "evening": [
                f"Good evening, {name}. Welcome home.",
                f"Good evening, {name}. I've been keeping watch.",
                f"Welcome back, {name}. Everything is in order.",
            ],
        }

        import random
        greeting = random.choice(greetings.get(time_of_day, greetings["afternoon"]))
        self.speak(greeting)
        return greeting

    def announce_intruder(self):
        """Alert about an unknown person."""
        self.speak("Alert. An unrecognized individual has been detected. "
                   "Recording their activity and capturing photos.")

    def announce_sleep_mode(self):
        """Announce entering sleep mode."""
        self.speak("No activity detected. Entering standby mode. "
                   "I'll keep watching and learning.")

    def announce_wake(self):
        """Announce waking from sleep."""
        self.speak("Motion detected. Resuming active monitoring.")

    def say_goodbye(self, owner_name: str = None):
        """Say goodbye when owner leaves."""
        name = owner_name or settings.OWNER_NAME
        self.speak(f"Goodbye, {name}. I'll keep the house secure.")

    def acknowledge_command(self, command: str):
        """Acknowledge a received command."""
        self.speak(f"Right away, {settings.OWNER_NAME}.")

    # ================================================================
    # Utilities
    # ================================================================
    def get_conversation_log(self, limit: int = 50) -> list:
        """Get recent conversation log."""
        return self._conversation_log[-limit:]

    def is_tts_available(self) -> bool:
        return self._tts_engine is not None

    def is_stt_available(self) -> bool:
        return (SR_AVAILABLE and self._recognizer is not None) or \
               (VOSK_AVAILABLE and self._vosk_model is not None)

    def cleanup(self):
        """Cleanup resources."""
        self._speak_queue.put(None)
        if self._speak_thread:
            self._speak_thread.join(timeout=2)


# Singleton
voice_service = VoiceService()
