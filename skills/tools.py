"""
FRIDAY tools — every function here is handed to Gemini as a callable tool.
Gemini decides when to call them based on what you say, and the SDK runs them
automatically. Each returns a SHORT string that gets folded into FRIDAY's reply.

Most functions delegate to FRIDAY's existing cross-platform skill modules
(apps/system/filesystem/browser/media_info_terminal); a few are new helpers.
"""
import os
import json
import platform
import threading
import webbrowser
import datetime

# Existing FRIDAY skill implementations (params-dict style) that we wrap.
from skills import apps as _apps
from skills import system as _system
from skills import filesystem as _fs
from skills import media_info_terminal as _mit

OS = platform.system()

# Local data (todos / notes) lives here.
DATA_DIR = os.path.join(os.path.expanduser("~"), ".friday", "data")
os.makedirs(DATA_DIR, exist_ok=True)
TODO_FILE = os.path.join(DATA_DIR, "todos.json")
NOTES_FILE = os.path.join(DATA_DIR, "notes.txt")

# Reminders that come due are queued here; the main loop speaks them.
due_reminders: list[str] = []


# ── Apps ─────────────────────────────────────────────────────────────────────

def open_app(app: str) -> str:
    """Open an application by name, e.g. 'whatsapp', 'chrome', 'notepad', 'vs code', 'spotify', 'calculator'."""
    return _apps.open_app({"app": app})


def close_app(app: str) -> str:
    """Close/quit a running application by name, e.g. 'chrome', 'spotify'."""
    return _apps.close_app({"app": app})


# ── Web & info ───────────────────────────────────────────────────────────────

def search_web(query: str) -> str:
    """Search the web and return the top results as text. Use this for current events,
    facts you are unsure of, prices, news, or anything that changes over time."""
    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, max_results=4))
        if not results:
            return "No results found."
        return " | ".join(f"{r.get('title', '')}: {r.get('body', '')[:200]}" for r in results)
    except Exception as e:
        return f"Search failed: {e}"


def open_website(url: str) -> str:
    """Open a website in the default browser. Pass a URL or a domain like 'youtube.com'."""
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."


def search_in_browser(query: str) -> str:
    """Open a Google search for the query in the default browser (use when the user
    wants to SEE search results on screen rather than hear a spoken answer)."""
    from urllib.parse import quote_plus
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Searching the web for {query}."


def get_weather(city: str = "current") -> str:
    """Get the current weather for a city (or 'current' for the current location)."""
    return _mit.get_weather({"location": city})


def get_time_and_date() -> str:
    """Get the current local time and date."""
    return _mit.get_time({})


# ── System control ───────────────────────────────────────────────────────────

def set_volume(percent: int) -> str:
    """Set the system output volume to a percentage from 0 to 100."""
    return _system.volume({"action": "set", "value": int(percent)})


def change_volume(direction: str) -> str:
    """Nudge the volume: pass 'up', 'down', or 'mute'."""
    return _system.volume({"action": direction.lower()})


def set_brightness(percent: int) -> str:
    """Set screen brightness to a percentage from 0 to 100."""
    return _system.brightness({"action": "set", "value": int(percent)})


def change_brightness(direction: str) -> str:
    """Nudge screen brightness: pass 'up' or 'down'."""
    return _system.brightness({"action": direction.lower()})


def set_wifi(enabled: bool) -> str:
    """Turn Wi-Fi on (enabled=true) or off (enabled=false)."""
    return _system.wifi({"action": "on" if enabled else "off"})


def connect_wifi(network: str) -> str:
    """Connect to a saved Wi-Fi network by name."""
    return _system.wifi({"action": "connect", "network": network})


def set_bluetooth(enabled: bool) -> str:
    """Turn Bluetooth on (enabled=true) or off (enabled=false)."""
    return _system.bluetooth({"action": "on" if enabled else "off"})


def media_control(action: str) -> str:
    """Control media playback: pass 'play', 'pause', 'next', 'previous', or 'stop'."""
    return _mit.control({"action": action.lower()})


def take_screenshot() -> str:
    """Take a screenshot and save it to the Desktop."""
    return _system.screenshot({})


def lock_screen() -> str:
    """Lock the computer screen."""
    return _system.lock_screen({})


def sleep_computer() -> str:
    """Put the computer to sleep."""
    return _system.sleep_system({})


def restart_computer() -> str:
    """Restart the computer (in a few seconds). Only when clearly asked."""
    return _system.restart_system({})


def shutdown_computer() -> str:
    """Shut down the computer (in a few seconds). Only when clearly asked."""
    return _system.shutdown_system({})


def system_status() -> str:
    """Report battery level, CPU and memory usage of this computer."""
    try:
        import psutil
        parts = [f"CPU at {psutil.cpu_percent(interval=0.4)} percent",
                 f"memory at {psutil.virtual_memory().percent} percent"]
        batt = psutil.sensors_battery()
        if batt:
            state = "charging" if batt.power_plugged else "on battery"
            parts.append(f"battery at {round(batt.percent)} percent, {state}")
        return ", ".join(parts) + "."
    except Exception as e:
        return f"Could not read system status: {e}"


def type_text(text: str) -> str:
    """Type text on the keyboard into whatever window is currently focused."""
    try:
        import pyautogui
        pyautogui.write(text, interval=0.02)
        return "Typed it."
    except Exception as e:
        return f"Could not type: {e}"


# ── Files ────────────────────────────────────────────────────────────────────

def create_file(path: str, is_folder: bool = False) -> str:
    """Create a new empty file, or a folder if is_folder=true. Path may use '~'."""
    return _fs.create({"path": path, "type": "folder" if is_folder else "file"})


def open_path(path: str) -> str:
    """Open a file or folder with its default program. Path may use '~'."""
    return _fs.open_file({"path": path})


def delete_path(path: str) -> str:
    """Delete a file or folder. Path may use '~'. Use with care."""
    return _fs.delete({"path": path})


def move_path(source: str, destination: str) -> str:
    """Move or rename a file/folder from source to destination. Paths may use '~'."""
    return _fs.move({"src": source, "dst": destination})


# ── Terminal ─────────────────────────────────────────────────────────────────

def run_command(command: str) -> str:
    """Run a shell command on the computer and return its output. Dangerous commands
    are blocked. Use only when the user clearly asks to run a command."""
    return _mit.run_command({"command": command})


# ── Reminders, todos, notes ──────────────────────────────────────────────────

def set_reminder(message: str, minutes: float) -> str:
    """Set a reminder that FRIDAY will say out loud after the given number of minutes."""
    def fire():
        due_reminders.append(f"Reminder: {message}")
    threading.Timer(float(minutes) * 60, fire).start()
    return f"Okay, I'll remind you in {float(minutes):g} minutes."


def _load_todos() -> list:
    if os.path.exists(TODO_FILE):
        try:
            return json.loads(open(TODO_FILE, encoding="utf-8").read())
        except Exception:
            return []
    return []


def add_todo(item: str) -> str:
    """Add an item to the to-do list."""
    todos = _load_todos()
    todos.append(item)
    open(TODO_FILE, "w", encoding="utf-8").write(json.dumps(todos, indent=2))
    return f"Added. You now have {len(todos)} items on your list."


def list_todos() -> str:
    """Read out the current to-do list."""
    todos = _load_todos()
    if not todos:
        return "Your to-do list is empty."
    return "Your list: " + "; ".join(f"{i + 1}, {t}" for i, t in enumerate(todos))


def clear_todos() -> str:
    """Clear the entire to-do list."""
    open(TODO_FILE, "w", encoding="utf-8").write("[]")
    return "Cleared your to-do list."


def take_note(text: str) -> str:
    """Save a quick timestamped note."""
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {text}\n")
    return "Noted."


# Everything Gemini is allowed to call:
ALL_TOOLS = [
    # apps
    open_app, close_app,
    # web & info
    search_web, open_website, search_in_browser, get_weather, get_time_and_date,
    # system
    set_volume, change_volume, set_brightness, change_brightness,
    set_wifi, connect_wifi, set_bluetooth, media_control, take_screenshot,
    lock_screen, sleep_computer, restart_computer, shutdown_computer,
    system_status, type_text,
    # files
    create_file, open_path, delete_path, move_path,
    # terminal
    run_command,
    # productivity
    set_reminder, add_todo, list_todos, clear_todos, take_note,
]
