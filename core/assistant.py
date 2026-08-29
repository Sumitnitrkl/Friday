"""
FRIDAY Core Assistant — orchestrates wake word, STT, AI, TTS, and skill execution
"""

import os
import time
import logging
import yaml
from core.listener import Listener
from core.speaker import Speaker
from core.brain import Brain
from skills import tools
from utils.network import is_online

logger = logging.getLogger("FRIDAY")


class Friday:
    def __init__(self, config_path="config.yaml"):
        self._load_config(config_path)
        self._setup_logging()
        logger.info("Initialising FRIDAY...")

        self.online = is_online(self.cfg["network"]["check_url"],
                                self.cfg["network"]["check_timeout"])
        logger.info(f"Network: {'ONLINE' if self.online else 'OFFLINE'}")

        self.speaker   = Speaker(self.cfg, self.online)
        self.listener  = Listener(self.cfg)
        self.brain     = Brain(self.cfg, self.online)

        self._running  = False

    # ------------------------------------------------------------------ #
    def _load_config(self, path):
        with open(path, "r") as f:
            self.cfg = yaml.safe_load(f)

    def _setup_logging(self):
        level = getattr(logging, self.cfg["system"].get("log_level", "INFO"))
        log_file = self.cfg["system"].get("log_file", "friday.log")
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),
            ],
        )

    # ------------------------------------------------------------------ #
    def greet(self):
        hour = time.localtime().tm_hour
        if hour < 12:
            period = "morning"
        elif hour < 17:
            period = "afternoon"
        else:
            period = "evening"

        greetings = [
            f"Hey! Good {period}. I'm FRIDAY — your personal assistant. What do you need?",
            f"Good {period}! FRIDAY here, ready to help. Just say the word.",
            f"Hey there! Good {period}. Systems are up and I'm all ears.",
        ]
        import random
        self.speaker.say(random.choice(greetings))

    # ------------------------------------------------------------------ #
    def run(self):
        """Main loop — listen → understand → act → speak"""
        self._running = True
        wake_words = [w.lower() for w in self.cfg["assistant"]["wake_words"]]
        followup_window = self.cfg["assistant"].get("followup_window", 2)
        followups_left = 0

        logger.info(f"Listening for wake words: {wake_words}")
        print(f"\nListening for: {wake_words}\n")

        while self._running:
            try:
                self._announce_reminders()

                if followups_left > 0:
                    # No wake word needed for a couple of turns after a reply.
                    print("[listening — follow-up]")
                    heard = self.listener.listen_active()
                    if not heard:
                        followups_left = 0
                        continue
                    command_text = self._extract_command(heard, wake_words)
                else:
                    raw = self.listener.listen_passive()
                    if not raw or not any(w in raw.lower() for w in wake_words):
                        continue
                    logger.info(f"Wake word detected in: '{raw}'")
                    self.speaker.chime()
                    command_text = self._extract_command(raw, wake_words)
                    if not command_text:
                        self.speaker.say("Yeah? What do you need?")
                        command_text = self.listener.listen_active()

                if not command_text:
                    continue

                logger.info(f"Command: '{command_text}'")
                print(f"[you] {command_text}")
                if not self._handle_command(command_text):
                    break
                followups_left = followup_window

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
                self.speaker.say("Something went wrong on my end. Try again.")

    def _announce_reminders(self):
        while tools.due_reminders:
            self.speaker.say(tools.due_reminders.pop(0))

    # ------------------------------------------------------------------ #
    def _extract_command(self, utterance: str, wake_words: list) -> str:
        """Strip wake word prefix and return remaining command text."""
        text = utterance.lower()
        for w in wake_words:
            if text.startswith(w):
                return utterance[len(w):].strip(" ,.")
        return ""

    EXIT_PHRASES = ("stop listening", "go to sleep", "goodbye friday", "shut yourself down")

    def _handle_command(self, text: str) -> bool:
        """Send text to the Gemini brain (which runs tools) and speak the reply.

        Returns False if FRIDAY should stop running.
        """
        low = text.lower().strip()

        if any(p in low for p in self.EXIT_PHRASES):
            self.speaker.say("Okay, going quiet. Say the wake word when you need me.")
            return False
        if low in ("reset", "new conversation", "forget everything"):
            self.brain.reset()
            self.speaker.say("Fresh start — I've cleared our conversation.")
            return True

        reply = self.brain.think(text)
        if reply:
            self.speaker.say(reply)
        return True
