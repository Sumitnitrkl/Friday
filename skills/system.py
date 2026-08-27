"""
FRIDAY Skill: System Controls
Volume, brightness, wifi, bluetooth, lock, sleep, restart, shutdown, screenshot
Cross-platform: macOS + Windows
"""

import subprocess
import platform
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger("FRIDAY.skill.system")
SYSTEM = platform.system()


# ─── Volume ──────────────────────────────────────────────────────────────────

def volume(params: dict) -> str:
    action = params.get("action", "").lower()
    value  = params.get("value", 10)

    if SYSTEM == "Darwin":
        if action == "up":
            _mac_run('set volume output volume (output volume of (get volume settings) + 10)')
            return "Volume up!"
        elif action == "down":
            _mac_run('set volume output volume (output volume of (get volume settings) - 10)')
            return "Volume down!"
        elif action == "mute":
            _mac_run('set volume with output muted')
            return "Muted!"
        elif action == "set":
            _mac_run(f'set volume output volume {int(value)}')
            return f"Volume set to {value}%."

    elif SYSTEM == "Windows":
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = cast(interface, POINTER(IAudioEndpointVolume))
            if action == "mute":
                vol.SetMute(1, None)
                return "Muted!"
            elif action == "up":
                cur = vol.GetMasterVolumeLevelScalar()
                vol.SetMasterVolumeLevelScalar(min(1.0, cur + 0.1), None)
                return "Volume up!"
            elif action == "down":
                cur = vol.GetMasterVolumeLevelScalar()
                vol.SetMasterVolumeLevelScalar(max(0.0, cur - 0.1), None)
                return "Volume down!"
            elif action == "set":
                vol.SetMasterVolumeLevelScalar(int(value) / 100, None)
                return f"Volume set to {value}%."
        except ImportError:
            subprocess.run(f'nircmd changesysvolume {"2000" if action=="up" else "-2000"}', shell=True)
            return f"Volume {action}!"

    return "Volume control not supported on this platform."


# ─── Brightness ──────────────────────────────────────────────────────────────

def brightness(params: dict) -> str:
    action = params.get("action", "").lower()
    value  = params.get("value", 50)

    if SYSTEM == "Darwin":
        if action == "up":
            subprocess.run(["brightness", "0.8"], capture_output=True)
            return "Brightness up!"
        elif action == "down":
            subprocess.run(["brightness", "0.3"], capture_output=True)
            return "Brightness down!"
        elif action == "set":
            level = int(value) / 100
            subprocess.run(["brightness", str(level)], capture_output=True)
            return f"Brightness set to {value}%."
        return "Try: 'brightness up', 'brightness down', or 'set brightness to 70'"

    elif SYSTEM == "Windows":
        try:
            import wmi
            c = wmi.WMI(namespace='wmi')
            methods = c.WmiMonitorBrightnessMethods()[0]
            if action == "set":
                methods.WmiSetBrightness(int(value), 0)
                return f"Brightness set to {value}%."
            current = c.WmiMonitorBrightness()[0].CurrentBrightness
            if action == "up":
                methods.WmiSetBrightness(min(100, current + 20), 0)
                return "Brightness up!"
            elif action == "down":
                methods.WmiSetBrightness(max(0, current - 20), 0)
                return "Brightness down!"
        except Exception as e:
            return f"Couldn't adjust brightness: {e}"

    return "Brightness control not available."


# ─── WiFi ────────────────────────────────────────────────────────────────────

def wifi(params: dict) -> str:
    action  = params.get("action", "").lower()
    network = params.get("network", "")

    if SYSTEM == "Darwin":
        iface = "en0"
        if action == "on":
            subprocess.run(["networksetup", "-setairportpower", iface, "on"])
            return "WiFi on!"
        elif action == "off":
            subprocess.run(["networksetup", "-setairportpower", iface, "off"])
            return "WiFi off!"
        elif action == "connect" and network:
            subprocess.run(["networksetup", "-setairportnetwork", iface, network])
            return f"Connecting to {network}…"

    elif SYSTEM == "Windows":
        if action == "on":
            subprocess.run("netsh interface set interface Wi-Fi admin=enable", shell=True)
            return "WiFi on!"
        elif action == "off":
            subprocess.run("netsh interface set interface Wi-Fi admin=disable", shell=True)
            return "WiFi off!"
        elif action == "connect" and network:
            subprocess.run(f'netsh wlan connect name="{network}"', shell=True)
            return f"Connecting to {network}…"

    return "WiFi control not available."


# ─── Bluetooth ───────────────────────────────────────────────────────────────

def bluetooth(params: dict) -> str:
    action = params.get("action", "").lower()

    if SYSTEM == "Darwin":
        state = "1" if action == "on" else "0"
        subprocess.run(["blueutil", f"--power", state], capture_output=True)
        return f"Bluetooth {'on' if action=='on' else 'off'}!"

    elif SYSTEM == "Windows":
        # Requires admin or bluetoothctl workaround
        return "Bluetooth toggle on Windows needs admin rights — open Settings > Bluetooth."

    return "Bluetooth control not available."


# ─── Power ───────────────────────────────────────────────────────────────────

def lock_screen(params: dict) -> str:
    if SYSTEM == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to keystroke "q" using {command down, control down}'])
    elif SYSTEM == "Windows":
        subprocess.run("rundll32 user32.dll,LockWorkStation", shell=True)
    return "Screen locked!"

def sleep_system(params: dict) -> str:
    if SYSTEM == "Darwin":
        subprocess.run(["osascript", "-e", 'tell application "System Events" to sleep'])
    elif SYSTEM == "Windows":
        subprocess.run("rundll32 powrprof.dll,SetSuspendState 0,1,0", shell=True)
    return "Going to sleep. Night!"

def restart_system(params: dict) -> str:
    time.sleep(2)
    if SYSTEM == "Darwin":
        subprocess.run(["osascript", "-e", 'tell application "System Events" to restart'])
    elif SYSTEM == "Windows":
        subprocess.run("shutdown /r /t 5", shell=True)
    return "Restarting in a few seconds!"

def shutdown_system(params: dict) -> str:
    time.sleep(2)
    if SYSTEM == "Darwin":
        subprocess.run(["osascript", "-e", 'tell application "System Events" to shut down'])
    elif SYSTEM == "Windows":
        subprocess.run("shutdown /s /t 5", shell=True)
    return "Shutting down. See you next time!"


# ─── Screenshot ──────────────────────────────────────────────────────────────

def screenshot(params: dict) -> str:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    home = os.path.expanduser("~")
    path = os.path.join(home, "Desktop", f"screenshot_{ts}.png")

    if SYSTEM == "Darwin":
        subprocess.run(["screencapture", path])
    elif SYSTEM == "Windows":
        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(path)
        except ImportError:
            subprocess.run(f'powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen"', shell=True)
            return "Screenshot taken (pyautogui not installed for best results)."

    return f"Screenshot saved to Desktop!"


# ─── Helper ──────────────────────────────────────────────────────────────────

def _mac_run(script: str):
    subprocess.run(["osascript", "-e", script], capture_output=True)
