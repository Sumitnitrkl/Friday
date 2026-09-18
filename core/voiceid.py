"""
FRIDAY Voice ID — lightweight speaker verification so FRIDAY only obeys you.

Approach (offline, free, no heavy ML): each utterance is turned into a compact
voice fingerprint from its MFCC statistics (mean + std of 20 MFCCs), L2-normalised.
Enrollment averages several of your samples into a stored "voiceprint"; at runtime
a command's fingerprint is compared to it by cosine similarity and accepted only
if it clears a threshold.

Enroll with:  python main.py --enroll
Tune with:    config.yaml -> security.voice_threshold
"""
import os
import io
import wave
import logging

import numpy as np

logger = logging.getLogger("FRIDAY.VoiceID")

DATA_DIR = os.path.join(os.path.expanduser("~"), ".friday", "data")
os.makedirs(DATA_DIR, exist_ok=True)
VOICEPRINT = os.path.join(DATA_DIR, "voiceprint.npy")


def _wav_to_signal(wav_bytes: bytes):
    wf = wave.open(io.BytesIO(wav_bytes), "rb")
    sr = wf.getframerate()
    ch = wf.getnchannels()
    raw = wf.readframes(wf.getnframes())
    wf.close()
    sig = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    if ch == 2:
        sig = sig.reshape(-1, 2).mean(axis=1)
    return sig, sr


def _embed(wav_bytes: bytes):
    """Turn WAV bytes into an L2-normalised voice fingerprint (or None if too short)."""
    from python_speech_features import mfcc
    from scipy.signal import resample_poly

    sig, sr = _wav_to_signal(wav_bytes)
    if sig.size < sr * 0.3:          # < 0.3s of audio — not enough to judge
        return None
    # Normalise device sample-rate to 16 kHz so fingerprints are comparable.
    if sr != 16000:
        sig = resample_poly(sig, 16000, sr)
        sr = 16000
    m = mfcc(sig, samplerate=sr, numcep=20, nfft=512)
    if m.shape[0] < 3:
        return None
    feat = np.concatenate([m.mean(axis=0), m.std(axis=0)])
    norm = np.linalg.norm(feat)
    return feat / norm if norm > 0 else feat


class VoiceID:
    def __init__(self, threshold: float = 0.80):
        self.threshold = float(threshold)
        self._ref = None
        if os.path.exists(VOICEPRINT):
            try:
                self._ref = np.load(VOICEPRINT)
            except Exception as e:
                logger.warning(f"Could not load voiceprint: {e}")

    def enrolled(self) -> bool:
        return self._ref is not None

    def verify(self, wav_bytes: bytes) -> bool:
        """True if this audio matches the enrolled voice (or if no voiceprint /
        an error — we never lock the user out on failure)."""
        if self._ref is None:
            return True
        try:
            emb = _embed(wav_bytes)
            if emb is None:
                return True
            score = float(np.dot(emb, self._ref))
            logger.info(f"voice match {score:.3f} (need >= {self.threshold})")
            return score >= self.threshold
        except Exception as e:
            logger.warning(f"voice verify error: {e}")
            return True

    def enroll(self, wav_list) -> bool:
        embs = [e for e in (_embed(w) for w in wav_list) if e is not None]
        if len(embs) < 2:
            return False
        ref = np.mean(embs, axis=0)
        ref = ref / np.linalg.norm(ref)
        np.save(VOICEPRINT, ref)
        self._ref = ref
        return True


# --------------------------------------------------------------------------- #
def enroll_interactive(samples: int = 6):
    """Record several samples of the user's voice and save a voiceprint."""
    try:
        import speech_recognition as sr
    except ImportError:
        print("Install SpeechRecognition + pyaudio first (pip install -r requirements.txt).")
        return

    r = sr.Recognizer()
    r.pause_threshold = 0.8

    # Optional spoken guidance so enrollment is hands-free (uses EDITH's voice).
    speak = None
    try:
        import yaml
        from core.speaker import Speaker
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = yaml.safe_load(open(os.path.join(root, "config.yaml"), encoding="utf-8"))
        speak = Speaker(cfg, online=True).say
    except Exception:
        speak = None

    def announce(msg, say=True):
        print(msg)
        if say and speak:
            try:
                speak(msg)
            except Exception:
                pass

    announce("Voice enrollment. Please do this in a quiet room. "
             "When I ask, repeat the phrase in your normal voice.")
    try:
        with sr.Microphone() as source:
            print("Calibrating microphone… stay quiet for a moment.")
            r.adjust_for_ambient_noise(source, duration=1.2)
    except Exception as e:
        announce(f"I couldn't access a microphone: {e}")
        return

    phrases = [
        "Hey Edith, it's me.",
        "Edith, only listen to my voice.",
        "This is my voice signature.",
        "Edith, you are my assistant.",
        "Recognise me by my voice.",
        "Good morning Edith.",
    ]
    wavs, i = [], 0
    while len(wavs) < samples:
        phrase = phrases[i % len(phrases)]
        i += 1
        announce(f"Please say: {phrase}")
        try:
            with sr.Microphone() as source:
                audio = r.listen(source, timeout=8, phrase_time_limit=5)
            wavs.append(audio.get_wav_data())
            print(f"  ✓ captured {len(wavs)}/{samples}\n")
        except Exception as e:
            print(f"  ✗ missed that ({e}); retrying\n")

    if VoiceID().enroll(wavs):
        announce("Enrollment complete. I will now respond only to your voice.")
        print("   If it ignores you, LOWER security.voice_threshold in config.yaml;")
        print("   if it still obeys others, RAISE it. (Default 0.80)")
    else:
        announce("Enrollment failed — I didn't get enough clear samples. "
                 "Please try again in a quieter spot.")
