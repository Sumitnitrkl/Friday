"""
FRIDAY Listener — Speech-to-Text via SpeechRecognition + Google's free recognizer.
No Whisper/ffmpeg needed; needs internet. Falls back to keyboard if no microphone.
"""
import logging

logger = logging.getLogger("FRIDAY.Listener")


class Listener:
    def __init__(self, cfg: dict):
        self.cfg  = cfg
        self.scfg = cfg["speech"]
        self._sr  = None
        self._mic_ok = False
        self._init()

    # ------------------------------------------------------------------ #
    def _init(self):
        try:
            import speech_recognition as sr
            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.scfg.get("energy_threshold", 300)
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8
            # Probe + calibrate the mic once.
            with sr.Microphone() as source:
                logger.info("Calibrating microphone for ambient noise…")
                self._recognizer.adjust_for_ambient_noise(source, duration=1.0)
            self._mic_ok = True
            logger.info("Microphone ready (Google STT)")
        except ImportError:
            logger.warning("speech_recognition not installed — pip install SpeechRecognition pyaudio")
        except Exception as e:
            logger.warning(f"Microphone unavailable ({e}) — falling back to keyboard input")

    # ------------------------------------------------------------------ #
    def listen_passive(self) -> str:
        """Short listen used to catch the wake word."""
        return self._capture(timeout=5, phrase_limit=6)

    def listen_active(self) -> str:
        """Longer listen after the wake word, for the actual command."""
        return self._capture(
            timeout=self.scfg.get("listen_timeout", 8),
            phrase_limit=self.scfg.get("phrase_time_limit", 15),
        )

    # ------------------------------------------------------------------ #
    def _capture(self, timeout, phrase_limit) -> str:
        if not self._mic_ok:
            return self._keyboard()

        sr = self._sr
        try:
            with sr.Microphone() as source:
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )
        except sr.WaitTimeoutError:
            return ""
        except Exception as e:
            logger.error(f"Audio capture error: {e}")
            return ""

        try:
            text = self._recognizer.recognize_google(audio)
            return (text or "").strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logger.error(f"Google STT request error: {e}")
            return ""

    # ------------------------------------------------------------------ #
    def _keyboard(self) -> str:
        try:
            return input("Type command: ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""
