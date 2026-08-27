"""
FRIDAY - Personal AI Assistant
Cross-platform (Windows/macOS), warm & casual personality
Online + offline hybrid mode
"""

import sys
import signal
import threading

# Ensure a bundled ffmpeg is on PATH before Whisper loads (fixes STT [WinError 2]).
from utils.ffmpeg_setup import ensure_ffmpeg_on_path
ensure_ffmpeg_on_path()

from core.assistant import Friday

def handle_exit(sig, frame):
    print("\n[FRIDAY] Shutting down... Goodbye!")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    friday = Friday()
    friday.greet()
    friday.run()
