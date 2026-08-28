"""
FRIDAY Skill: App Control
Cross-platform open/close for macOS and Windows
"""

import subprocess
import platform
import logging
import json
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


def _windows_start_apps():
    """All Start-menu apps (Store + desktop) as a list of {Name, AppID}."""
    ps = "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress"
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, text=True, timeout=10,
    )
    data = json.loads(out.stdout or "[]")
    return data if isinstance(data, list) else [data]


def _resolve_windows_app(candidates):
    """AppID + display name of the first Start app matching any candidate name."""
    try:
        apps = _windows_start_apps()
    except Exception as e:
        logger.warning(f"Get-StartApps lookup failed: {e}")
        return None, None

    names = [c.lower().strip() for c in candidates if c]
    for want in names:                       # exact match wins
        for a in apps:
            if a.get("Name", "").lower() == want:
                return a.get("AppID"), a.get("Name")
    for want in names:                       # then substring
        for a in apps:
            if want and want in a.get("Name", "").lower():
                return a.get("AppID"), a.get("Name")
    return None, None


def open_app(params: dict) -> str:
    app_name = params.get("app", "").lower().strip()
    alias    = APP_ALIASES.get(app_name)

    try:
        if SYSTEM == "Darwin":
            name = alias["mac"] if alias else app_name.title()
            subprocess.Popen(["open", "-a", name])
            return f"Opening {name}!"

        elif SYSTEM == "Windows":
            # Resolve by Start-menu name so Store apps (WhatsApp, etc.) and
            # desktop apps both launch reliably, via their AppUserModelID.
            candidates = [app_name]
            if alias:
                candidates += [alias.get("mac", ""),
                               (alias.get("win") or "").replace(".exe", "")]
            app_id, display = _resolve_windows_app(candidates)
            if app_id:
                subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
                return f"Opening {display}!"

            # Fallbacks: a known launch command, then a bare start.
            if alias and alias.get("cmd_win"):
                subprocess.Popen(alias["cmd_win"], shell=True)
            else:
                subprocess.Popen(f'start "" "{app_name}"', shell=True)
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
