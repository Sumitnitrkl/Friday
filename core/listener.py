"""
FRIDAY Listener — Speech-to-Text
Primary:  OpenAI Whisper (local, offline)
Fallback: SpeechRecognition + Google (online)
"""

import logging
import queue
import threading
import tempfile
import os

logger = logging.getLogger("FRIDAY.Listener")


class Listener:
    def __init__(self, cfg: dict):
        self.cfg     = cfg
        self.scfg    = cfg["speech"]
        self.engine  = self.scfg.get("stt_engine", "whisper")
        self._whisper_model = None
        self._sr     = None
        self._mic    = None
        self._init_engines()

    # ------------------------------------------------------------------ #
    def _init_engines(self):
        try:
            import speech_recognition as sr
            self._sr  = sr
            self._mic = sr.Microphone()
            logger.info("SpeechRecognition microphone ready")
        except ImportError:
            logger.warning("speech_recognition not installed — pip install SpeechRecognition pyaudio")

        if self.engine == "whisper":
            try:
                import whisper
                model_size = self.scfg.get("whisper_model", "base")
                logger.info(f"Loading Whisper model: {model_size} …")
                self._whisper_model = whisper.load_model(model_size)
                logger.info("Whisper model loaded")
            except ImportError:
                logger.warning("whisper not installed — pip install openai-whisper")
                self.engine = "google"

    # ------------------------------------------------------------------ #
    def listen_passive(self) -> str:
        """Lightweight always-on listen — just detects speech and returns text."""
        return self._capture_audio(timeout=None, phrase_timeout=3)

    def listen_active(self) -> str:
        """Active listen after wake word — longer phrase timeout."""
        timeout      = self.scfg.get("listen_timeout", 8)
        phrase_timeout = self.scfg.get("phrase_timeout", 3)
        return self._capture_audio(timeout=timeout, phrase_timeout=phrase_timeout)

    # ------------------------------------------------------------------ #
    def _capture_audio(self, timeout, phrase_timeout) -> str:
        if not self._sr or not self._mic:
            return self._fallback_input()

        sr = self._sr
        try:
            with self._mic as source:
                self._sr.Recognizer().adjust_for_ambient_noise(source, duration=0.3)
                r = sr.Recognizer()
                r.energy_threshold = self.scfg.get("energy_threshold", 300)
                r.dynamic_energy_threshold = True
                audio = r.listen(source, timeout=timeout,
                                  phrase_time_limit=phrase_timeout)

            return self._transcribe(audio)

        except sr.WaitTimeoutError:
            return ""
        except Exception as e:
            logger.error(f"Audio capture error: {e}")
            return ""

    # ------------------------------------------------------------------ #
    def _transcribe(self, audio) -> str:
        """Transcribe AudioData using Whisper or Google fallback."""
        if self._whisper_model:
            return self._transcribe_whisper(audio)
        return self._transcribe_google(audio)

    def _transcribe_whisper(self, audio) -> str:
        import whisper, numpy as np, io, wave
        sr = self._sr
        try:
            wav_data = audio.get_wav_data()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_data)
                tmp_path = f.name

            result = self._whisper_model.transcribe(tmp_path, language="en", fp16=False)
            os.unlink(tmp_path)
            text = result.get("text", "").strip()
            logger.debug(f"Whisper: '{text}'")
            return text
        except Exception as e:
            logger.warning(f"Whisper failed, trying Google: {e}")
            return self._transcribe_google(audio)

    def _transcribe_google(self, audio) -> str:
        sr = self._sr
        try:
            text = sr.Recognizer().recognize_google(audio)
            logger.debug(f"Google STT: '{text}'")
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logger.error(f"Google STT request error: {e}")
            return ""

    # ------------------------------------------------------------------ #
    def _fallback_input(self) -> str:
        """Keyboard fallback when microphone is unavailable."""
        try:
            return input("Type command: ")
        except (EOFError, KeyboardInterrupt):
            return ""
