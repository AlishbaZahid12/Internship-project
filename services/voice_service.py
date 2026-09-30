"""
Voice input/output helpers. Responses are spoken in whichever language
the person last spoke in - English or Urdu - switching automatically
based on what was heard, rather than always speaking both.
"""

import threading
import time
from contextlib import contextmanager

from core.interfaces import SpeechToTextEngine, TextToSpeechEngine
from core.logger import get_logger
from utils.helpers import extract_digits, extract_choice, is_affirmative, is_negative

logger = get_logger(__name__)


class VoiceService:

    def __init__(self, stt: SpeechToTextEngine, tts: TextToSpeechEngine):
        self.stt = stt
        self.tts = tts
        self._mic_lock = threading.Lock()
        self._paused = threading.Event()
        self._speaking = False
        self._last_speech_end = 0.0
        self._current_lang = "en"          # switches based on what was last heard
        self._translation_cache = {}

    # ---------------- output ----------------

    def speak(self, text: str) -> None:
        """Speaks in the currently active language only (English or Urdu)."""
        if self._current_lang == "ur":
            urdu_text = self._translate_to_urdu(text)
            print(f"[SPEAK-UR] {urdu_text or text}")
            self._speaking = True
            try:
                self.tts.speak(urdu_text or text, lang="ur")
            finally:
                self._speaking = False
                self._last_speech_end = time.time()
        else:
            print(f"[SPEAK-EN] {text}")
            self._speaking = True
            try:
                self.tts.speak(text, lang="en")
            finally:
                self._speaking = False
                self._last_speech_end = time.time()

    def _translate_to_urdu(self, text: str) -> str:
        if text in self._translation_cache:
            return self._translation_cache[text]
        try:
            from deep_translator import GoogleTranslator
            urdu = GoogleTranslator(source="en", target="ur").translate(text)
            self._translation_cache[text] = urdu
            return urdu
        except Exception as e:
            logger.warning(f"Urdu translation failed, using English instead: {e}")
            return ""

    def speech_overlapped(self, since: float) -> bool:
        return self._speaking or self._last_speech_end >= since

    # ---------------- background listener control ----------------

    @contextmanager
    def listener_paused(self):
        self._paused.set()
        try:
            yield
        finally:
            self._paused.clear()

    def is_listener_paused(self) -> bool:
        return self._paused.is_set()

    # ---------------- input ----------------

    def listen(self, timeout: int = None, phrase_time_limit: int = None,
               quiet: bool = False) -> str:
        with self._mic_lock:
            answer = self.stt.listen(timeout=timeout, phrase_time_limit=phrase_time_limit)

        if answer:
            # Switch the active language to whatever was just heard
            detected = getattr(self.stt, "last_language", "en")
            if detected != self._current_lang:
                logger.info(f"Switching active language: {self._current_lang} -> {detected}")
            self._current_lang = detected

        if not quiet:
            print(f"[HEARD-{self._current_lang}] '{answer}'")
        return answer

    def ask_text(self, prompt: str, retries: int = 2) -> str:
        for _ in range(retries):
            self.speak(prompt)
            answer = self.listen()
            if answer:
                return answer
            self.speak("I didn't catch that.")

        self.speak("Voice isn't working well right now. Please type your answer instead.")
        return input(f"{prompt} (type here): ").strip()

    def ask_confirmed_text(self, prompt: str, retries: int = 2) -> str:
        for _ in range(retries):
            answer = self.ask_text(prompt, retries=retries)
            if not answer:
                continue
            if self.ask_yes_no(f"I heard: {answer}. Is that correct?"):
                return answer
            self.speak("Okay, let's try again.")
        return ""

    def ask_pin(self, prompt: str, digit_length: int = 4, retries: int = 2) -> str:
        for _ in range(retries):
            self.speak(prompt)
            digits = extract_digits(self.listen())

            if len(digits) == digit_length:
                if self.ask_yes_no(f"I heard the PIN: {' '.join(digits)}. Is that correct?"):
                    return digits
                self.speak("Okay, let's try again.")
            else:
                self.speak(f"I heard {len(digits)} digits, but I need exactly {digit_length}.")

        self.speak("Voice isn't picking up your PIN clearly. Please type it instead.")
        typed = input(f"Type your {digit_length}-digit PIN: ").strip()
        return typed if typed.isdigit() and len(typed) == digit_length else ""

    def ask_digits(self, prompt: str, min_length: int, max_length: int, retries: int = 2) -> str:
        for _ in range(retries):
            self.speak(prompt)
            digits = extract_digits(self.listen())

            if min_length <= len(digits) <= max_length:
                if self.ask_yes_no(f"I heard {' '.join(digits)}. Is that correct?"):
                    return digits
                self.speak("Okay, let's try again.")
            else:
                self.speak(f"I heard {len(digits)} digits, which doesn't look right.")

        self.speak("Voice isn't picking up the number clearly. Please type it instead.")
        typed = "".join(c for c in input("Type the number: ") if c.isdigit())
        return typed if min_length <= len(typed) <= max_length else ""

    def ask_yes_no(self, prompt: str, retries: int = 2) -> bool:
        for _ in range(retries):
            self.speak(prompt)
            answer = self.listen()

            if is_affirmative(answer):
                return True
            if is_negative(answer):
                return False

            self.speak("Please say yes or no.")

        self.speak("Please type y for yes or n for no.")
        return input("Type y/n: ").strip().lower().startswith("y")

    def ask_menu(self, prompt: str, option_count: int, retries: int = 2):
        for _ in range(retries):
            self.speak(prompt)
            number = extract_choice(self.listen())
            if number is not None and 1 <= number <= option_count:
                return number
            self.speak(f"Please say a number from one to {option_count}.")

        self.speak("Please type the number instead.")
        typed = input(f"Type a number 1-{option_count}: ").strip()
        if typed.isdigit() and 1 <= int(typed) <= option_count:
            return int(typed)
        return None

    def ask_choice(self, prompt: str, items: list, retries: int = 2):
        listing = ". ".join(f"{i}: {item}" for i, item in enumerate(items, start=1))

        for _ in range(retries):
            self.speak(f"{prompt} {listing}. Say the number, or say cancel.")
            number = extract_choice(self.listen())

            if number == 0:
                return None
            if number is not None and 1 <= number <= len(items):
                return number - 1
            self.speak("I didn't get a valid number.")

        self.speak("Please type the number instead, or 0 to cancel.")
        typed = input("Type a number: ").strip()
        if typed.isdigit() and 1 <= int(typed) <= len(items):
            return int(typed) - 1
        return None