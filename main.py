"""
FRIDAY - Personal AI Assistant
Cross-platform (Windows/macOS), warm & casual personality, Gemini-powered agent.

Run:
    python main.py          voice assistant (terminal)
    python main.py --ui     voice assistant + holographic HUD in the browser
"""

import sys
import signal

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

    # One-time voice enrollment: python main.py --enroll
    if "--enroll" in sys.argv:
        from core.voiceid import enroll_interactive
        enroll_interactive()
        sys.exit(0)

    if "--ui" in sys.argv:
        # Desktop app window (native window hosting the HUD)
        from ui.server import UIServer
        from ui.app import launch
        ui = UIServer()
        ui.start()
        friday = Friday(ui=ui)
        launch(friday, ui)      # blocks until the window is closed
        sys.exit(0)

    # Terminal mode
    friday = Friday()
    friday.greet()
    friday.run()
