"""
FRIDAY - Personal AI Assistant
Cross-platform (Windows/macOS), warm & casual personality
Online + offline hybrid mode
"""

import sys
import signal
import threading

# Load .env (API keys like GEMINI_API_KEY) before anything reads the environment.
from dotenv import load_dotenv
load_dotenv()

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
