"""
FRIDAY Skill Dispatcher — routes parsed intents to skill handlers
"""

import logging
from skills import apps, browser, filesystem, system, media, info, terminal

logger = logging.getLogger("FRIDAY.Dispatcher")
def _general_chat(params: dict) -> str:
    return params.get("message", "I didn't quite catch that.")

def _unknown(params: dict) -> str:
    return "I'm not sure how to help with that yet, but I'm learning!"
# Maps intent names → handler functions
SKILL_MAP = {
    # Apps
    "open_app":          apps.open_app,
    "close_app":         apps.close_app,
    # Browser / web
    "web_search":        browser.web_search,
    "open_url":          browser.open_url,
    # File system
    "file_create":       filesystem.create,
    "file_open":         filesystem.open_file,
    "file_delete":       filesystem.delete,
    "file_move":         filesystem.move,
    # System controls
    "system_volume":     system.volume,
    "system_brightness": system.brightness,
    "system_wifi":       system.wifi,
    "system_bluetooth":  system.bluetooth,
    "lock_screen":       system.lock_screen,
    "sleep_system":      system.sleep_system,
    "restart_system":    system.restart_system,
    "shutdown_system":   system.shutdown_system,
    "take_screenshot":   system.screenshot,
    # Media
    "media_control":     media.control,
    # Info
    "get_time":          info.get_time,
    "get_weather":       info.get_weather,
    "set_reminder":      info.set_reminder,
    # Terminal
    "run_terminal":      terminal.run_command,
    # Catch-all
    "general_chat":      _general_chat,
    "unknown":           _unknown,
}


class Dispatcher:
    def __init__(self, cfg: dict, speaker):
        self.cfg     = cfg
        self.speaker = speaker

    def execute(self, intent: dict, raw_text: str) -> str:
        """Execute the intent and return the spoken response."""
        name   = intent.get("intent", "unknown")
        params = intent.get("params", {})
        pre_response = intent.get("response", "")

        # Speak the pre-response immediately (feels more responsive)
        if pre_response and self.cfg["system"].get("speak_confirmations", True):
            # Only speak pre-response for action intents, not info/chat
            if name not in ("get_time", "get_weather", "general_chat", "unknown"):
                self.speaker.say(pre_response)

        handler = SKILL_MAP.get(name, _unknown)
        try:
            result = handler(params)
            logger.info(f"Skill '{name}' result: {result}")
            return result or pre_response
        except Exception as e:
            logger.error(f"Skill '{name}' error: {e}", exc_info=True)
            return f"Something went wrong trying to do that — {e}"


# ------------------------------------------------------------------ #

