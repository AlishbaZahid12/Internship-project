"""
Text-to-speech using gTTS + pygame.
"""

import os
import tempfile
import time
import traceback

import pygame
from gtts import gTTS

from core.interfaces import TextToSpeechEngine


class GTTSTextToSpeech(TextToSpeechEngine):

    def speak(self, text: str, lang: str = "en") -> None:
        if not text or not text.strip():
            return

        path = None
        try:
            tts = gTTS(text=text, lang=lang)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                path = f.name
            tts.save(path)

            file_size = os.path.getsize(path)
            print(f"[TTS] Saved audio file: {path} ({file_size} bytes)")

            try:
                pygame.mixer.quit()
            except Exception:
                pass
            pygame.mixer.init()

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

            # Give playback a moment to actually start before checking -
            # calling get_busy() immediately after play() can wrongly
            # read False before SDL has started the stream.
            time.sleep(0.3)

            waited = 0.0
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                waited += 0.1

            print(f"[TTS] Finished playing after {waited:.1f}s of active playback.")
            pygame.mixer.music.unload()

        except Exception:
            print("=" * 50)
            print("TTS PLAYBACK ERROR:")
            traceback.print_exc()
            print("=" * 50)
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass