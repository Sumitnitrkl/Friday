"""
FRIDAY Skill: App Control
Cross-platform open/close for macOS and Windows
"""

import subprocess
import platform
import logging
import psutil

logger = logging.getLogger("FRIDAY.skill.apps")

SYSTEM = platform.system()

# Common app name aliases → actual app/process names
APP_ALIASES = {
    # Browsers
    "chrome":        {"mac": "Google Chrome", "win": "chrome.exe",       "cmd_win": "start chrome"},
    "firefox":       {"mac": "Firefox",        "win": "firefox.exe",      "cmd_win": "start firefox"},
    "safari":        {"mac": "Safari",         "win": None,               "cmd_win": None},
    "edge":          {"mac": "Microsoft Edge", "win": "msedge.exe",       "cmd_win": "start msedge"},
    # Productivity
    "vscode":        {"mac": "Visual Studio Code", "win": "Code.exe",     "cmd_win": "code"},
    "vs code":       {"mac": "Visual Studio Code", "win": "Code.exe",     "cmd_win": "code"},
    "word":          {"mac": "Microsoft Word", "win": "WINWORD.EXE",      "cmd_win": "start winword"},
    "excel":         {"mac": "Microsoft Excel","win": "EXCEL.EXE",        "cmd_win": "start excel"},
    "powerpoint":    {"mac": "Microsoft PowerPoint","win": "POWERPNT.EXE","cmd_win": "start powerpnt"},
    "notes":         {"mac": "Notes",          "win": "notepad.exe",      "cmd_win": "notepad"},
    "notepad":       {"mac": "TextEdit",       "win": "notepad.exe",      "cmd_win": "notepad"},
    "calculator":    {"mac": "Calculator",     "win": "calc.exe",         "cmd_win": "calc"},
    "calendar":      {"mac": "Calendar",       "win": None,               "cmd_win": "start outlookcal:"},
    "finder":        {"mac": "Finder",         "win": "explorer.exe",     "cmd_win": "explorer"},
    "explorer":      {"mac": "Finder",         "win": "explorer.exe",     "cmd_win": "explorer"},
    # Communication
    "slack":         {"mac": "Slack",          "win": "slack.exe",        "cmd_win": "start slack"},
    "zoom":          {"mac": "zoom.us",        "win": "Zoom.exe",         "cmd_win": "start zoom"},
    "discord":       {"mac": "Discord",        "win": "Discord.exe",      "cmd_win": "start discord"},
    "whatsapp":      {"mac": "WhatsApp",       "win": "WhatsApp.exe",     "cmd_win": "start whatsapp"},
    "mail":          {"mac": "Mail",           "win": "outlook.exe",      "cmd_win": "start outlook"},
    "outlook":       {"mac": "Microsoft Outlook","win": "OUTLOOK.EXE",    "cmd_win": "start outlook"},
    # Media
    "spotify":       {"mac": "Spotify",        "win": "Spotify.exe",      "cmd_win": "start spotify"},
    "vlc":           {"mac": "VLC",            "win": "vlc.exe",          "cmd_win": "start vlc"},
    # Utilities
    "terminal":      {"mac": "Terminal",       "win": "cmd.exe",          "cmd_win": "start cmd"},
    "settings":      {"mac": "System Preferences","win": "ms-settings:",  "cmd_win": "start ms-settings:"},
    "task manager":  {"mac": "Activity Monitor","win": "taskmgr.exe",     "cmd_win": "taskmgr"},
}


def open_app(params: dict) -> str:
    app_name = params.get("app", "").lower().strip()
    alias    = APP_ALIASES.get(app_name)

    try:
        if SYSTEM == "Darwin":
            name = alias["mac"] if alias else app_name.title()
            subprocess.Popen(["open", "-a", name])
            return f"Opening {name}!"

        elif SYSTEM == "Windows":
            if alias and alias.get("cmd_win"):
                subprocess.Popen(alias["cmd_win"], shell=True)
            else:
                subprocess.Popen(["start", app_name], shell=True)
            return f"Opening {app_name}!"

        else:
            subprocess.Popen([app_name])
            return f"Launched {app_name}!"

    except FileNotFoundError:
        return f"Couldn't find {app_name} — is it installed?"
    except Exception as e:
        logger.error(f"open_app error: {e}")
        return f"Had trouble opening {app_name}."


def close_app(params: dict) -> str:
    app_name = params.get("app", "").lower().strip()
    alias    = APP_ALIASES.get(app_name)
    killed   = []

    # Determine process name to kill
    if alias:
        proc_name = alias["win"] if SYSTEM == "Windows" else alias["mac"]
    else:
        proc_name = app_name

    if not proc_name:
        return f"I can't close {app_name} on this system."

    proc_name_lower = proc_name.lower()

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc_name_lower in proc.info["name"].lower():
                proc.terminate()
                killed.append(proc.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        return f"Closed {', '.join(set(killed))}."
    else:
        # macOS: try `pkill -f`
        if SYSTEM == "Darwin":
            subprocess.run(["pkill", "-f", proc_name], capture_output=True)
            return f"Sent close signal to {app_name}."
        return f"Couldn't find {app_name} running."
