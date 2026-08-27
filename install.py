#!/usr/bin/env python3
"""
FRIDAY Virtual Environment Setup
Creates venv, installs all dependencies, and launches FRIDAY.
Works on macOS and Windows.
Run: python install.py
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
SYSTEM   = platform.system()
HERE     = Path(__file__).parent.resolve()
VENV_DIR = HERE / "venv"
REQ_FILE = HERE / "requirements.txt"

# Python executable inside venv
if SYSTEM == "Windows":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_PIP    = VENV_DIR / "Scripts" / "pip.exe"
    ACTIVATE    = VENV_DIR / "Scripts" / "activate.bat"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_PIP    = VENV_DIR / "bin" / "pip"
    ACTIVATE    = VENV_DIR / "bin" / "activate"


def banner(text):
    print(f"\n{'─'*50}")
    print(f"  {text}")
    print(f"{'─'*50}")


def run(cmd, **kwargs):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"  ⚠️  Command failed (exit {result.returncode})")
    return result


def check_python():
    banner("Checking Python version")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")
    if version < (3, 9):
        print("  ❌ FRIDAY requires Python 3.9+. Please upgrade.")
        sys.exit(1)
    print("  ✅ Python version OK")


def create_venv():
    banner("Creating virtual environment")
    if VENV_DIR.exists():
        print(f"  Virtual environment already exists at: {VENV_DIR}")
        choice = input("  Recreate it? [y/N]: ").strip().lower()
        if choice == "y":
            import shutil
            shutil.rmtree(VENV_DIR)
            print("  Removed old venv.")
        else:
            print("  Using existing venv.")
            return

    run([sys.executable, "-m", "venv", str(VENV_DIR)])
    print(f"  ✅ Venv created at: {VENV_DIR}")


def upgrade_pip():
    banner("Upgrading pip inside venv")
    run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"])


def install_requirements():
    banner("Installing FRIDAY requirements")

    # First install wheel to avoid build errors
    run([str(VENV_PIP), "install", "wheel", "setuptools"])

    if SYSTEM == "Darwin":
        _install_mac()
    elif SYSTEM == "Windows":
        _install_windows()

    # Install main requirements
    run([str(VENV_PIP), "install", "-r", str(REQ_FILE)])
    print("\n  ✅ Requirements installed")


def _install_mac():
    print("\n  Installing macOS-specific dependencies...")
    # Check for homebrew
    result = subprocess.run(["which", "brew"], capture_output=True, text=True)
    if not result.stdout.strip():
        print("  ⚠️  Homebrew not found. Install from https://brew.sh for best experience.")
        print("      Some features (audio, brightness) may not work without it.")
        return

    brew_packages = ["ffmpeg", "portaudio", "mpg123"]
    for pkg in brew_packages:
        check = subprocess.run(["brew", "list", pkg], capture_output=True)
        if check.returncode != 0:
            print(f"  Installing {pkg} via brew...")
            subprocess.run(["brew", "install", pkg])
        else:
            print(f"  {pkg} already installed ✓")

    # PyAudio needs portaudio first
    run([str(VENV_PIP), "install", "pyaudio"])


def _install_windows():
    print("\n  Installing Windows-specific dependencies...")
    # Try pipwin for pyaudio
    run([str(VENV_PIP), "install", "pipwin"])
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "pipwin", "install", "pyaudio"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("  ⚠️  PyAudio via pipwin failed. Trying direct install...")
        run([str(VENV_PIP), "install", "pyaudio"])

    # Windows audio/volume control
    run([str(VENV_PIP), "install", "pycaw", "comtypes"])
    # Windows WMI for brightness
    run([str(VENV_PIP), "install", "wmi"])


def create_launchers():
    banner("Creating launch scripts")

    # macOS/Linux shell script
    sh_path = HERE / "start_friday.sh"
    sh_path.write_text(f"""#!/bin/bash
# FRIDAY Launcher — activates venv and starts assistant
cd "{HERE}"
source "{ACTIVATE}"
python main.py "$@"
""")
    sh_path.chmod(0o755)
    print(f"  ✅ macOS/Linux: {sh_path}")

    # Windows batch file
    bat_path = HERE / "start_friday.bat"
    bat_path.write_text(f"""@echo off
REM FRIDAY Launcher — activates venv and starts assistant
cd /d "{HERE}"
call "{ACTIVATE}"
python main.py %*
""")
    print(f"  ✅ Windows:     {bat_path}")

    # macOS app-like double-click (AppleScript wrapper)
    if SYSTEM == "Darwin":
        app_sh = HERE / "FRIDAY.command"
        app_sh.write_text(f"""#!/bin/bash
cd "{HERE}"
source "{ACTIVATE}"
python main.py
""")
        app_sh.chmod(0o755)
        print(f"  ✅ macOS double-click: {app_sh}")


def update_autostart():
    banner("Updating auto-start to use venv")

    # Update setup_autostart.py to reference venv python
    autostart = HERE / "setup_autostart.py"
    content = autostart.read_text(encoding="utf-8")

    # Replace sys.executable with venv python path
    old = "PYTHON   = sys.executable"
    new = f"""# Use venv Python if available, else system Python
_VENV_PY = Path(__file__).parent / "venv" / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
PYTHON   = str(_VENV_PY) if _VENV_PY.exists() else sys.executable"""

    if old in content:
        content = content.replace(old, new)
        autostart.write_text(content, encoding="utf-8")
        print("  ✅ setup_autostart.py updated to use venv Python")
    else:
        print("  ℹ️  setup_autostart.py already updated or manually edited")


def print_summary():
    banner("✨ FRIDAY Setup Complete!")

    if SYSTEM == "Darwin":
        print(f"""
  How to run FRIDAY:

  Option A — Terminal:
    cd {HERE}
    source venv/bin/activate
    python main.py

  Option B — Double-click:
    Open Finder → double-click  FRIDAY.command

  Option C — Shell script:
    ./start_friday.sh

  To run at startup:
    python setup_autostart.py
""")
    elif SYSTEM == "Windows":
        print(f"""
  How to run FRIDAY:

  Option A — Double-click:
    start_friday.bat

  Option B — Command Prompt:
    cd {HERE}
    venv\\Scripts\\activate
    python main.py

  To run at startup:
    python setup_autostart.py
""")

    print("  📌 Don't forget to set your Claude API key:")
    if SYSTEM == "Windows":
        print("     set ANTHROPIC_API_KEY=your-key-here")
    else:
        print("     export ANTHROPIC_API_KEY=your-key-here")
    print("  Or add it directly in config.yaml → ai.claude_api_key\n")


if __name__ == "__main__":
    print("\n🤖 FRIDAY — Virtual Environment Setup")
    print(f"   Platform: {SYSTEM} | Python: {sys.version.split()[0]}")
    print(f"   Location: {HERE}")

    check_python()
    create_venv()
    upgrade_pip()
    install_requirements()
    create_launchers()
    update_autostart()
    print_summary()
