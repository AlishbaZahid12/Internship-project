"""
Concrete pyttsx3 (offline) implementation of the TextToSpeechEngine interface.
"""

import pyttsx3
from core.interfaces import TextToSpeechEngine
from core.logger import get_logger

logger = get_logger(__name__)


class Pyttsx3TextToSpeech(TextToSpeechEngine):

    def __init__(self, rate: int = 165, volume: float = 1.0):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)

    def speak(self, text: str) -> None:
        logger.info(f"Speaking: {text}")
        self.engine.say(text)
        self.engine.runAndWait()