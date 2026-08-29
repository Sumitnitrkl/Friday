"""
FRIDAY Brain — Gemini with automatic function calling over FRIDAY's skills.

Gemini receives every tool in skills.tools.ALL_TOOLS and decides which to call
(possibly several, chained) based on what you say. The google-genai SDK runs the
chosen tools automatically and Gemini returns a short spoken reply.
"""
import os
import logging

from google import genai
from google.genai import types

from skills.tools import ALL_TOOLS

logger = logging.getLogger("FRIDAY.Brain")

DEFAULT_PERSONALITY = (
    "You are FRIDAY, a warm, friendly, and capable AI voice assistant running on "
    "your creator's personal computer. Speak naturally and warmly, like a helpful "
    "friend. Keep replies SHORT (1-2 sentences) because they are spoken aloud. "
    "Never use markdown, bullet points, emojis, or special characters. When asked "
    "to do something on the computer, USE YOUR TOOLS to actually do it instead of "
    "explaining how. After a tool runs, confirm briefly and warmly. For general "
    "questions, just answer conversationally."
)


class Brain:
    def __init__(self, cfg: dict, online: bool):
        self.cfg    = cfg
        self.acfg   = cfg["ai"]
        self.online = online
        self.model  = self.acfg.get("gemini_model", "gemini-3.5-flash-lite")
        self.personality = self.acfg.get("personality", DEFAULT_PERSONALITY)
        self.api_key = (
            self.acfg.get("gemini_api_key")
            or os.environ.get("GEMINI_API_KEY", "")
            or os.environ.get("GOOGLE_API_KEY", "")
        )
        self._client = None
        self._chat = None

    # ------------------------------------------------------------------ #
    def _get_chat(self):
        if self._chat is None:
            if not self.api_key:
                raise RuntimeError(
                    "No GEMINI_API_KEY found — put it in your .env file "
                    "(get a free key at https://aistudio.google.com/apikey)."
                )
            self._client = genai.Client(api_key=self.api_key)
            self._chat = self._client.chats.create(
                model=self.model,
                config=types.GenerateContentConfig(
                    system_instruction=self.personality,
                    tools=ALL_TOOLS,   # SDK auto-executes these when Gemini calls them
                    temperature=0.7,
                ),
            )
        return self._chat

    # ------------------------------------------------------------------ #
    def think(self, text: str) -> str:
        """Send the user's words to Gemini (it may call tools), return a spoken reply."""
        try:
            response = self._get_chat().send_message(text)
            reply = (response.text or "").strip()
            return reply or "Done!"
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                logger.warning("Gemini rate limit hit (free tier)")
                return "I'm getting a lot of requests right now. Give me a few seconds, then try again."
            if "API key" in msg or "PERMISSION_DENIED" in msg or "401" in msg:
                logger.error(f"Gemini auth error: {e}")
                return "My API key seems to be missing or invalid. Please check the key in your dot env file."
            logger.error(f"Brain error: {e}")
            return "Sorry, my brain hit a snag. Could you say that again?"

    # ------------------------------------------------------------------ #
    def reset(self):
        """Forget the conversation and start a fresh chat session."""
        self._chat = None
