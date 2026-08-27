"""
FRIDAY Speaker — Text-to-Speech
Primary:  edge-tts (Microsoft Neural, online) — warm Irish English voice
Fallback: pyttsx3 (fully offline)
"""

import logging
import asyncio
import threading
import os
import tempfile
import platform
import subprocess

logger = logging.getLogger("FRIDAY.Speaker")

CHIME_CHAR = "\a"


class Speaker:
    def __init__(self, cfg: dict, online: bool):
        self.cfg    = cfg
        self.vcfg   = cfg["voice"]
        self.online = online
        self._lock  = threading.Lock()
        self._pyttsx3_engine = None
        self._init_offline()

    def _init_offline(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate",   self.vcfg.get("pyttsx3_rate",   175))
            engine.setProperty("volume", self.vcfg.get("pyttsx3_volume", 1.0))

            voices = engine.getProperty("voices")
            for v in voices:
                if any(k in v.name.lower() for k in ["female", "zira", "samantha", "victoria", "hazel"]):
                    engine.setProperty("voice", v.id)
                    break

            self._pyttsx3_engine = engine
            logger.info("pyttsx3 offline TTS ready")
        except Exception as e:
            logger.warning(f"pyttsx3 unavailable: {e}")

    def say(self, text: str):
        logger.info(f"Speaking: '{text}'")
        print(f"\nFRIDAY: {text}\n")

        with self._lock:
            if self.online and self.vcfg.get("online_engine") == "edge_tts":
                try:
                    self._speak_edge(text)
                    return
                except Exception as e:
                    logger.warning(f"edge-tts failed, falling back: {e}")

            self._speak_pyttsx3(text)

    def _speak_edge(self, text: str):
        import edge_tts
        voice = self.vcfg.get("edge_tts_voice", "en-IE-EmilyNeural")

        async def _run():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp)
            return tmp

        tmp = asyncio.run(_run())
        self._play_audio(tmp)
        os.unlink(tmp)

    def _speak_pyttsx3(self, text: str):
        if self._pyttsx3_engine:
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
        else:
            print(f"[TTS unavailable] {text}")

    def _play_audio(self, path: str):
        system = platform.system()
        try:
            if system == "Darwin":
                os.system(f"afplay '{path}'")
            elif system == "Windows":
                os.system(f'ffplay -nodisp -autoexit -loglevel quiet "{path}"')
            else:
                os.system(f"ffplay -nodisp -autoexit -loglevel quiet '{path}'")
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            self._speak_pyttsx3(path)

    def chime(self):
        print("[chime]", end="", flush=True)
        system = platform.system()
        try:
            if system == "Darwin":
                os.system("afplay /System/Library/Sounds/Tink.aiff")
            elif system == "Windows":
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            else:
                print(CHIME_CHAR, end="", flush=True)
        except Exception:
            pass