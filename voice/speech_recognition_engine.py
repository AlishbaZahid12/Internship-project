"""
Captures speech from the microphone. Tries English first; if that isn't
understood, retries the SAME recording as Urdu - so a person can speak
either language without picking one in advance.
"""

import time
import speech_recognition as sr
from core.interfaces import SpeechToTextEngine
from core.logger import get_logger

logger = get_logger(__name__)


class GoogleSpeechToText(SpeechToTextEngine):

    def __init__(self, timeout: int = 8, phrase_time_limit: int = 10):
        self.recognizer = sr.Recognizer()
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.recognizer.pause_threshold = 1.2
        self.recognizer.dynamic_energy_threshold = True
        self._last_calibration = 0.0

    def listen(self, timeout: int = None, phrase_time_limit: int = None) -> str:
        timeout = timeout or self.timeout
        phrase_time_limit = phrase_time_limit or self.phrase_time_limit

        with sr.Microphone() as source:
            if time.time() - self._last_calibration > 60:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
                self._last_calibration = time.time()
            try:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            except sr.WaitTimeoutError:
                logger.debug("No speech detected within timeout.")
                return ""

        # Try English first
        try:
            text = self.recognizer.recognize_google(audio, language="en-US")
            logger.info(f"Recognized (en): {text}")
            return text.lower().strip()
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return ""

        # Fall back to Urdu on the same recording
        try:
            text = self.recognizer.recognize_google(audio, language="ur-PK")
            logger.info(f"Recognized (ur): {text}")
            return text.strip()
        except sr.UnknownValueError:
            logger.debug("Speech was not understood in English or Urdu.")
            return ""
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return ""