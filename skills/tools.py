"""
FRIDAY tools — every function here is handed to Gemini as a callable tool.
Gemini decides when to call them based on what you say, and the SDK runs them
automatically. Each returns a SHORT string that gets folded into FRIDAY's reply.

Most functions delegate to FRIDAY's existing cross-platform skill modules
(apps/system/filesystem/browser/media_info_terminal); a few are new helpers.
"""
import os
import re
import json
import time
import platform
import threading
import subprocess
import webbrowser
import datetime
from urllib.parse import quote

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
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.json")
MUSIC_FILE = os.path.join(DATA_DIR, "music_history.json")

WHATSAPP_SEND_DELAY = 7   # seconds to let the chat load before pressing Enter

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


# ── Full computer control (PowerShell) + inspection ──────────────────────────

# Raw-disk / drive-wiping operations — ALWAYS blocked, regardless of anything else.
_RAW_DISK = re.compile(
    r"(\bformat\b\s+[a-z]:|\bformat\s+/|format-volume|\bdiskpart\b|\bmkfs\b|"
    r"clear-disk|remove-partition|cipher\s+/w)", re.I)

# A destructive VERB (deletes, powers off, kills, changes system state).
_DESTRUCTIVE_VERB = re.compile(
    r"(remove-item|\brm\b|\bdel\b|\brmdir\b|\brd\b|stop-computer|restart-computer|"
    r"\bshutdown\b|stop-process|\bkill\b|set-executionpolicy|uninstall-|disable-|"
    r"reg(\.exe)?\s+delete|clear-content)", re.I)

# A dangerous TARGET for a destructive verb: a drive root (C:\ alone), the
# Windows/Program Files trees, or the Users root itself (but NOT files inside a
# user's own folder like C:\Users\Name\Desktop\x.txt — those just need confirm).
_DANGER_TARGET = re.compile(
    r"([a-z]:\\(\s|$|['\"]|\*|-)|"
    r"[a-z]:\\windows\b|"
    r"[a-z]:\\program files( \(x86\))?\b|"
    r"[a-z]:\\users(\s|$|['\"]))", re.I)


def run_powershell(command: str, confirmed: bool = False) -> str:
    """Run a PowerShell command to control ANY part of the computer — files, apps,
    settings, network, processes, installed software, and more. This is your general
    'do anything' tool. For DESTRUCTIVE or irreversible actions (deleting files,
    shutting down, killing processes, changing system settings), you MUST confirm
    with the user first, then call again with confirmed=True."""
    destructive = bool(_DESTRUCTIVE_VERB.search(command))
    catastrophic = bool(_RAW_DISK.search(command)) or \
        (destructive and bool(_DANGER_TARGET.search(command)))
    if catastrophic:
        return ("I won't run that — it targets a whole drive or a core system "
                "location and could permanently damage the computer.")
    if destructive and not confirmed:
        return (f"CONFIRM_NEEDED: this looks destructive -> [{command}]. Ask the user to "
                "confirm out loud; only if they clearly agree, call run_powershell again "
                "with the same command and confirmed=true.")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", command],
                           capture_output=True, text=True, timeout=60)
        out = (r.stdout or r.stderr or "").strip()
        return f"Done. {out[:1000]}" if out else "Done."
    except subprocess.TimeoutExpired:
        return "That command ran too long, so I stopped it."
    except Exception as e:
        return f"Command failed: {e}"


def read_file(path: str) -> str:
    """Read and return the text contents of a file (first ~4000 chars). Path may use '~'."""
    p = os.path.expanduser(path)
    if not os.path.exists(p):
        return f"There's no file at {p}."
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            data = f.read(4000)
        return data or "That file is empty."
    except Exception as e:
        return f"Couldn't read that: {e}"


def list_directory(path: str = "~") -> str:
    """List the files and folders in a directory. Path may use '~'."""
    p = os.path.expanduser(path)
    if not os.path.isdir(p):
        return f"{p} isn't a folder."
    try:
        entries = sorted(os.listdir(p))
        return ", ".join(entries[:60]) if entries else f"{p} is empty."
    except Exception as e:
        return f"Couldn't list that: {e}"


def find_files(name: str, root: str = "~") -> str:
    """Search for files or folders whose name contains the given text, under a root folder."""
    base = os.path.expanduser(root)
    hits, scanned = [], 0
    try:
        for dirpath, dirs, files in os.walk(base):
            scanned += 1
            if scanned > 3000:
                break
            for n in files + dirs:
                if name.lower() in n.lower():
                    hits.append(os.path.join(dirpath, n))
                    if len(hits) >= 20:
                        return "Found: " + "; ".join(hits)
    except Exception as e:
        return f"Search error: {e}"
    return "Found: " + "; ".join(hits) if hits else f"No matches for '{name}' under {base}."


def system_info() -> str:
    """Report OS, CPU, memory and disk summary for this computer."""
    import psutil
    vm = psutil.virtual_memory()
    du = psutil.disk_usage(os.path.expanduser("~"))
    return (f"{platform.system()} {platform.release()}, {psutil.cpu_count()} cores at "
            f"{psutil.cpu_percent(interval=0.3)} percent, memory {vm.percent} percent used, "
            f"disk {du.percent} percent used, {du.free // (1024**3)} gigabytes free.")


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


# ── WhatsApp messaging (contacts + auto-send) ────────────────────────────────

def _open_uri(uri: str):
    if OS == "Windows":
        subprocess.Popen(f'start "" "{uri}"', shell=True)
    elif OS == "Darwin":
        subprocess.Popen(["open", uri])
    else:
        subprocess.Popen(["xdg-open", uri])


def _load_contacts() -> dict:
    if os.path.exists(CONTACTS_FILE):
        try:
            return json.loads(open(CONTACTS_FILE, encoding="utf-8").read())
        except Exception:
            return {}
    return {}


def _save_contacts(c: dict):
    open(CONTACTS_FILE, "w", encoding="utf-8").write(json.dumps(c, indent=2))


def _resolve_contact(contact: str):
    name = contact.strip().lower()
    contacts = _load_contacts()
    if name in contacts:
        return contacts[name]
    digits = "".join(ch for ch in contact if ch.isdigit())
    return digits or None


def add_contact(name: str, phone: str) -> str:
    """Save a WhatsApp contact so you can message them by name later.
    The phone number MUST include the country code, e.g. 919876543210."""
    number = "".join(ch for ch in phone if ch.isdigit())
    if len(number) < 7:
        return "That doesn't look like a valid phone number — include the country code."
    contacts = _load_contacts()
    contacts[name.strip().lower()] = number
    _save_contacts(contacts)
    return f"Saved {name} as {number}."


def list_contacts() -> str:
    """List the saved WhatsApp contacts."""
    contacts = _load_contacts()
    if not contacts:
        return "You have no saved contacts yet."
    return "Contacts: " + ", ".join(f"{k} ({v})" for k, v in contacts.items())


def send_whatsapp(contact: str, message: str) -> str:
    """Send a WhatsApp message to a saved contact name or a phone number (with
    country code). Opens the chat with the message and sends it automatically."""
    number = _resolve_contact(contact)
    if not number:
        return (f"I don't have a number for {contact}. "
                f"Say: add contact {contact} followed by their number with country code.")
    _open_uri(f"whatsapp://send?phone={number}&text={quote(message)}")
    try:
        import pyautogui
        time.sleep(WHATSAPP_SEND_DELAY)   # wait for the chat to load
        pyautogui.press("enter")
        return f"Message sent to {contact}."
    except Exception as e:
        return f"I opened the chat with your message, but couldn't auto-send ({e}). Just press Enter."


# ── Music (YouTube auto-play / Spotify) ──────────────────────────────────────

def _load_music() -> list:
    if os.path.exists(MUSIC_FILE):
        try:
            return json.loads(open(MUSIC_FILE, encoding="utf-8").read())
        except Exception:
            return []
    return []


def _record_music(song: str, platform_name: str):
    hist = _load_music()
    hist.append({"song": song, "platform": platform_name,
                 "ts": datetime.datetime.now().isoformat(timespec="seconds")})
    open(MUSIC_FILE, "w", encoding="utf-8").write(json.dumps(hist[-100:], indent=2))


def _youtube_first_video(query: str):
    import requests
    r = requests.get("https://www.youtube.com/results?search_query=" + quote(query),
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
    ids = re.findall(r'"videoId":"([\w-]{11})"', r.text)
    return ids[0] if ids else None


def play_on_youtube(song: str) -> str:
    """Play a song, artist, or video on YouTube by name — auto-plays the first
    result in the browser. Use when the user says to play something on YouTube."""
    vid = None
    try:
        vid = _youtube_first_video(song)
    except Exception:
        pass
    if vid:
        webbrowser.open(f"https://www.youtube.com/watch?v={vid}")
    else:
        webbrowser.open("https://www.youtube.com/results?search_query=" + quote(song))
    _record_music(song, "youtube")
    return f"Playing {song} on YouTube."


def play_on_spotify(song: str) -> str:
    """Open a song or artist in the Spotify app by name (ready to play). Use when
    the user says to play something on Spotify. Note: true auto-play of a specific
    track requires Spotify Premium."""
    try:
        _open_uri(f"spotify:search:{quote(song)}")
    except Exception as e:
        return f"Could not open Spotify: {e}"
    _record_music(song, "spotify")
    return f"Opening {song} on Spotify for you."


def play_recent_music() -> str:
    """Play music from what was played before, for when the user asks to just
    'play some music' or 'play something' without naming a song."""
    import random
    hist = _load_music()
    if not hist:
        return "I don't know your taste yet — tell me a song to play and I'll remember it."
    pick = random.choice(hist[-10:])
    song, platform_name = pick["song"], pick.get("platform", "youtube")
    return play_on_spotify(song) if platform_name == "spotify" else play_on_youtube(song)


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
    # full computer control + inspection
    run_powershell, read_file, list_directory, find_files, system_info,
    # productivity
    set_reminder, add_todo, list_todos, clear_todos, take_note,
    # messaging + music control
    add_contact, list_contacts, send_whatsapp,
    play_on_youtube, play_on_spotify, play_recent_music,
]
