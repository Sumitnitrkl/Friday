#!/usr/bin/env python3
"""
FRIDAY Auto-start Setup
Installs FRIDAY to run automatically at system startup.
Run: python setup_autostart.py
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

if platform.system() == "Windows":
    import winreg

SYSTEM   = platform.system()
HERE     = Path(__file__).parent.resolve()
MAIN     = HERE / "main.py"

# Prefer venv Python if it exists, fall back to system Python
_venv_py = HERE / ("venv/Scripts/python.exe" if platform.system() == "Windows" else "venv/bin/python")
PYTHON   = str(_venv_py) if _venv_py.exists() else sys.executable

# Launcher scripts (use these instead of calling python directly, so venv is activated)
LAUNCHER_MAC = HERE / "start_friday.sh"
LAUNCHER_WIN = HERE / "start_friday.bat"


def setup_mac():
    plist_label = "com.friday.assistant"
    plist_path  = Path.home() / "Library/LaunchAgents" / f"{plist_label}.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    # Use the shell launcher so venv is activated automatically
    launcher = str(LAUNCHER_MAC) if LAUNCHER_MAC.exists() else str(PYTHON)

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{plist_label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{launcher}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{HERE}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{HERE}/friday.log</string>
    <key>StandardErrorPath</key>
    <string>{HERE}/friday_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>{os.environ.get('ANTHROPIC_API_KEY', '')}</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>"""

    plist_path.write_text(plist)
    subprocess.run(["launchctl", "load", str(plist_path)])
    print(f"✅ FRIDAY installed as macOS LaunchAgent: {plist_path}")
    print("   It will start automatically on next login.")
    print("   To start now: launchctl start com.friday.assistant")
    print("   To stop:      launchctl stop com.friday.assistant")
    print("   To remove:    launchctl unload", plist_path)


def setup_windows():
    # Use batch launcher so venv activates automatically
    launcher = str(LAUNCHER_WIN) if LAUNCHER_WIN.exists() else f'"{PYTHON}" "{MAIN}"'
    cmd = f'"{launcher}"' if LAUNCHER_WIN.exists() else launcher

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "FRIDAY", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        print(f"✅ FRIDAY added to Windows startup registry.")
        print(f"   Command: {cmd}")
        print("   It will start automatically on next login.")
        print("   To remove: open regedit → HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run → delete FRIDAY")
    except Exception as e:
        print(f"❌ Failed to set registry key: {e}")
        print("   Try running as Administrator.")

        # Fallback: startup folder
        startup = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        bat = startup / "FRIDAY.bat"
        bat.write_text(f'@echo off\nstart "" "{PYTHON}" "{MAIN}"\n')
        print(f"   Fallback: created startup batch file at {bat}")


def check_requirements():
    print("Checking requirements...")
    result = subprocess.run(
        [PYTHON, "-m", "pip", "install", "-r", str(HERE / "requirements.txt")],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ All requirements installed.")
    else:
        print("⚠️  Some requirements failed. Check requirements.txt manually.")
        print(result.stderr[:500])


if __name__ == "__main__":
    print(f"\n🤖 FRIDAY Auto-start Setup")
    print(f"   Platform: {SYSTEM}")
    print(f"   Python:   {PYTHON}")
    print(f"   Location: {HERE}\n")

    choice = input("Install requirements first? [Y/n]: ").strip().lower()
    if choice != "n":
        check_requirements()

    if SYSTEM == "Darwin":
        setup_mac()
    elif SYSTEM == "Windows":
        setup_windows()
    else:
        print("Linux: add to ~/.bashrc or create a systemd user service.")
        print(f"  ExecStart={PYTHON} {MAIN}")

    print("\n✨ Setup complete! FRIDAY is ready.")
