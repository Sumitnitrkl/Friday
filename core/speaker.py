"""
FRIDAY Speaker — Text-to-Speech
Primary:  edge-tts (Microsoft Neural, online) — warm, natural voice
Fallback: pyttsx3 (fully offline)
Playback: pygame (plays mp3 directly, no ffplay/ffmpeg needed)
"""
import logging
import asyncio
import threading
import os
import tempfile
import platform

logger = logging.getLogger("FRIDAY.Speaker")


class Speaker:
    def __init__(self, cfg: dict, online: bool):
        self.cfg    = cfg
        self.vcfg   = cfg["voice"]
        self.online = online
        self._lock  = threading.Lock()
        self._pyttsx3_engine = None
        self._mixer_ok = False
        self._init_playback()
        self._init_offline()

    def _init_playback(self):
        try:
            import pygame
            pygame.mixer.init()
            self._mixer_ok = True
            logger.info("pygame audio ready")
        except Exception as e:
            logger.warning(f"pygame audio unavailable ({e}); will use offline voice")

    def _init_offline(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate",   self.vcfg.get("pyttsx3_rate",   175))
            engine.setProperty("volume", self.vcfg.get("pyttsx3_volume", 1.0))
            for v in engine.getProperty("voices"):
                if any(k in v.name.lower() for k in ["female", "zira", "samantha", "victoria", "hazel"]):
                    engine.setProperty("voice", v.id)
                    break
            self._pyttsx3_engine = engine
            logger.info("pyttsx3 offline TTS ready")
        except Exception as e:
            logger.warning(f"pyttsx3 unavailable: {e}")

    # ------------------------------------------------------------------ #
    def say(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        logger.info(f"Speaking: '{text}'")
        print(f"\nFRIDAY: {text}\n")

        with self._lock:
            if self.online and self.vcfg.get("online_engine") == "edge_tts" and self._mixer_ok:
                try:
                    self._speak_edge(text)
                    return
                except Exception as e:
                    logger.warning(f"edge-tts failed, falling back to offline: {e}")
            self._speak_pyttsx3(text)

    # ------------------------------------------------------------------ #
    def _speak_edge(self, text: str):
        import edge_tts
        voice = self.vcfg.get("edge_tts_voice", "en-US-JennyNeural")

        async def _run(path):
            await edge_tts.Communicate(text, voice).save(path)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        try:
            asyncio.run(_run(tmp))
            self._play(tmp)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _play(self, path: str):
        import pygame
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(20)
        pygame.mixer.music.unload()

    def _speak_pyttsx3(self, text: str):
        if self._pyttsx3_engine:
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
        else:
            print(f"[TTS unavailable] {text}")

    # ------------------------------------------------------------------ #
    def chime(self):
        print("[chime]", end="", flush=True)
        try:
            if platform.system() == "Darwin":
                os.system("afplay /System/Library/Sounds/Tink.aiff")
            elif platform.system() == "Windows":
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            else:
                print("\a", end="", flush=True)
        except Exception:
            pass
