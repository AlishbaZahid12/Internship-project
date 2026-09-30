"""
Uses pyttsx3 (offline, proven reliable) for English, and gTTS (needs
internet, supports Urdu) only when speaking Urdu. A fresh pyttsx3
engine is created for every call - reusing one instance across many
calls on Windows can cause longer sentences to cut off partway through.
"""

import os
import tempfile
import time
import traceback

import pyttsx3
import pygame
from gtts import gTTS

from core.interfaces import TextToSpeechEngine


class HybridTextToSpeech(TextToSpeechEngine):

    def speak(self, text: str, lang: str = "en") -> None:
        if not text or not text.strip():
            return

        if lang == "en":
            self._speak_pyttsx3(text)
        else:
            self._speak_gtts(text, lang)

    def _speak_pyttsx3(self, text: str) -> None:
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            engine.setProperty("volume", 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            del engine
        except Exception:
            print("TTS (English) PLAYBACK ERROR:")
            traceback.print_exc()

    def _speak_gtts(self, text: str, lang: str) -> None:
        path = None
        try:
            tts = gTTS(text=text, lang=lang)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                path = f.name
            tts.save(path)

            try:
                pygame.mixer.quit()
            except Exception:
                pass
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            time.sleep(0.3)
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
        except Exception:
            print("TTS (Urdu) PLAYBACK ERROR:")
            traceback.print_exc()
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass