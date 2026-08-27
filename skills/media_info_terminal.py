"""
FRIDAY Skills: Media, Info, Terminal
"""

import subprocess
import platform
import logging
import requests
from datetime import datetime

logger = logging.getLogger("FRIDAY.skills")
SYSTEM = platform.system()


# ════════════════════════════════════════════════════════════════════════════
# MEDIA
# ════════════════════════════════════════════════════════════════════════════

def control(params: dict) -> str:
    action = params.get("action", "").lower()

    if SYSTEM == "Darwin":
        key_map = {
            "play":     "key code 49",       # space
            "pause":    "key code 49",
            "next":     "key code 124 using {command down}",
            "previous": "key code 123 using {command down}",
            "stop":     "key code 49",
        }
        script = f'tell application "System Events" to {key_map.get(action, "key code 49")}'
        subprocess.run(["osascript", "-e", script], capture_output=True)
        return f"Media: {action}!"

    elif SYSTEM == "Windows":
        try:
            import pyautogui
            key_map = {"play": "playpause", "pause": "playpause",
                       "next": "nexttrack", "previous": "prevtrack", "stop": "stop"}
            pyautogui.press(key_map.get(action, "playpause"))
            return f"Media: {action}!"
        except ImportError:
            return "Install pyautogui for media control: pip install pyautogui"

    return f"Media {action} not supported on this platform."


# ════════════════════════════════════════════════════════════════════════════
# INFO
# ════════════════════════════════════════════════════════════════════════════

def get_time(params: dict) -> str:
    now = datetime.now()
    hour   = now.strftime("%I").lstrip("0")
    minute = now.strftime("%M")
    period = now.strftime("%p")
    day    = now.strftime("%A, %B %-d") if SYSTEM != "Windows" else now.strftime("%A, %B %d").replace(" 0", " ")
    return f"It's {hour}:{minute} {period} — {day}."


def get_weather(params: dict) -> str:
    location = params.get("location", "current")
    try:
        # wttr.in is free, no API key needed
        url = f"https://wttr.in/{quote_plus(location)}?format=3"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.text.strip()
        return "Couldn't fetch weather right now."
    except Exception as e:
        return f"Weather check failed: {e}"


def set_reminder(params: dict) -> str:
    text = params.get("text", "")
    time_str = params.get("time", "")

    if SYSTEM == "Darwin":
        script = f'''
        tell application "Reminders"
            make new reminder with properties {{name:"{text}"}}
        end tell
        '''
        subprocess.run(["osascript", "-e", script], capture_output=True)
        return f"Reminder set: '{text}'!"
    elif SYSTEM == "Windows":
        # Open Cortana / Windows reminder
        return f"Reminder '{text}' noted — Windows reminders need Cortana or a third-party app."
    return f"Reminder set: '{text}'!"


# ════════════════════════════════════════════════════════════════════════════
# TERMINAL
# ════════════════════════════════════════════════════════════════════════════

BLOCKED_COMMANDS = ["rm -rf /", "format", "del /f /s /q c:\\", "mkfs", ":(){:|:&};:"]

def run_command(params: dict) -> str:
    cmd = params.get("command", "").strip()
    if not cmd:
        return "What command should I run?"

    # Safety check
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd.lower():
            return f"That command looks dangerous — I won't run it for safety."

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        output = (result.stdout or result.stderr or "").strip()[:500]
        if output:
            return f"Done! Output: {output}"
        return "Command ran successfully."
    except subprocess.TimeoutExpired:
        return "That command timed out after 30 seconds."
    except Exception as e:
        return f"Command failed: {e}"


# ─── helper ──────────────────────────────────────────────────────────────────
try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus
