"""
FRIDAY Brain — Natural Language Understanding
Online:  Gemini (free) / Groq (free) / Claude API
Offline: Ollama (llama3 local model) -> rule-based
Returns structured intent dict for the Dispatcher.
"""

import os
import json
import logging
import requests

logger = logging.getLogger("FRIDAY.Brain")

SYSTEM_PROMPT = """You are FRIDAY, a warm and casual AI assistant running on someone's personal computer.
Your job is to parse voice commands and return a structured JSON intent.

Return ONLY valid JSON with this structure:
{
  "intent": "<intent_name>",
  "params": { ... },
  "response": "<what to say to the user>"
}

Intent names and their params:
- open_app         : {"app": "app_name"}
- close_app        : {"app": "app_name"}
- web_search       : {"query": "search text", "browser": "default"}
- open_url         : {"url": "https://..."}
- file_create      : {"path": "~/...", "type": "file|folder"}
- file_open        : {"path": "~/..."}
- file_delete      : {"path": "~/..."}
- file_move        : {"src": "~/...", "dst": "~/..."}
- system_volume    : {"action": "up|down|mute|set", "value": 0-100}
- system_brightness: {"action": "up|down|set", "value": 0-100}
- system_wifi      : {"action": "on|off|connect", "network": "name"}
- system_bluetooth : {"action": "on|off"}
- media_control    : {"action": "play|pause|next|previous|stop"}
- run_terminal     : {"command": "shell command"}
- get_time         : {}
- get_weather      : {"location": "city or 'current'"}
- set_reminder     : {"text": "...", "time": "HH:MM or natural language"}
- take_screenshot  : {}
- lock_screen      : {}
- sleep_system     : {}
- restart_system   : {}
- shutdown_system  : {}
- general_chat     : {"message": "user message"}
- unknown          : {}

The "response" field should be warm, casual, short (1–2 sentences). Sound like a helpful friend.
Examples of FRIDAY's voice:
  "On it!" / "Sure, opening that now." / "Got it, searching for that." / "Done!" / "Alright, shutting down in a sec!"
"""


class Brain:
    def __init__(self, cfg: dict, online: bool):
        self.cfg    = cfg
        self.acfg   = cfg["ai"]
        self.online = online
        self._conversation = []  # keeps context

        self.api_key = (
            self.acfg.get("claude_api_key")
            or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self.groq_key = (
            self.acfg.get("groq_api_key")
            or os.environ.get("GROQ_API_KEY", "")
        )
        self.gemini_key = (
            self.acfg.get("gemini_api_key")
            or os.environ.get("GEMINI_API_KEY", "")
            or os.environ.get("GOOGLE_API_KEY", "")
        )

    # ------------------------------------------------------------------ #
    def parse(self, text: str) -> dict:
        """Parse natural language command into structured intent.

        Priority: online backend (Groq/Claude) -> Ollama (local) -> rule-based.
        """
        if self.online:
            backend = self.acfg.get("online_backend", "gemini")
            try:
                if backend == "gemini" and self.gemini_key:
                    return self._parse_gemini(text)
                if backend == "groq" and self.groq_key:
                    return self._parse_groq(text)
                if backend == "claude_api" and self.api_key:
                    return self._parse_claude(text)
                # Configured backend has no key — use whatever key is available.
                if self.gemini_key:
                    return self._parse_gemini(text)
                if self.groq_key:
                    return self._parse_groq(text)
                if self.api_key:
                    return self._parse_claude(text)
            except Exception as e:
                logger.warning(f"Online AI ({backend}) failed, trying Ollama: {e}")

        try:
            return self._parse_ollama(text)
        except Exception as e:
            logger.warning(f"Ollama failed, using rule-based: {e}")
            return self._rule_based(text)

    # ------------------------------------------------------------------ #
    def _parse_claude(self, text: str) -> dict:
        """Use Claude API for intent parsing."""
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)

        self._conversation.append({"role": "user", "content": text})
        if len(self._conversation) > 10:
            self._conversation = self._conversation[-10:]

        response = client.messages.create(
            model=self.acfg.get("claude_model", "claude-sonnet-5"),
            max_tokens=self.acfg.get("max_tokens", 500),
            system=SYSTEM_PROMPT,
            messages=self._conversation,
        )

        raw = response.content[0].text.strip()
        self._conversation.append({"role": "assistant", "content": raw})

        return self._safe_parse_json(raw)

    # ------------------------------------------------------------------ #
    def _parse_groq(self, text: str) -> dict:
        """Use Groq's free, OpenAI-compatible API for intent parsing."""
        self._conversation.append({"role": "user", "content": text})
        if len(self._conversation) > 10:
            self._conversation = self._conversation[-10:]

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.acfg.get("groq_model", "llama-3.3-70b-versatile"),
                "max_tokens": self.acfg.get("max_tokens", 500),
                # SYSTEM_PROMPT mentions "JSON", which json_object mode requires.
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + self._conversation,
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        self._conversation.append({"role": "assistant", "content": raw})
        return self._safe_parse_json(raw)

    # ------------------------------------------------------------------ #
    def _parse_gemini(self, text: str) -> dict:
        """Use Google Gemini's free API for intent parsing."""
        self._conversation.append({"role": "user", "content": text})
        if len(self._conversation) > 10:
            self._conversation = self._conversation[-10:]

        # Gemini uses role "model" (not "assistant") and a parts[] structure.
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in self._conversation
        ]

        model = self.acfg.get("gemini_model", "gemini-2.0-flash")
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.gemini_key,
            },
            json={
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": self.acfg.get("max_tokens", 500),
                    "responseMimeType": "application/json",
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        self._conversation.append({"role": "assistant", "content": raw})
        return self._safe_parse_json(raw)

    # ------------------------------------------------------------------ #
    def _parse_ollama(self, text: str) -> dict:
        """Use local Ollama model for intent parsing."""
        model = self.acfg.get("ollama_model", "llama3")
        prompt = f"{SYSTEM_PROMPT}\n\nUser command: {text}\n\nJSON:"

        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        return self._safe_parse_json(raw)

    # ------------------------------------------------------------------ #
    def _rule_based(self, text: str) -> dict:
        """Minimal rule-based fallback for common commands."""
        t = text.lower().strip()

        rules = [
            (["open ", "launch ", "start "],  self._rule_open),
            (["close ", "quit ", "exit "],    self._rule_close),
            (["search for ", "search ", "google ", "look up "], self._rule_search),
            (["volume up", "turn up"],        lambda _: {"intent":"system_volume","params":{"action":"up"},"response":"Turning volume up!"}),
            (["volume down", "turn down"],    lambda _: {"intent":"system_volume","params":{"action":"down"},"response":"Turning volume down!"}),
            (["mute"],                        lambda _: {"intent":"system_volume","params":{"action":"mute"},"response":"Muted!"}),
            (["play"],                        lambda _: {"intent":"media_control","params":{"action":"play"},"response":"Playing!"}),
            (["pause", "stop music"],         lambda _: {"intent":"media_control","params":{"action":"pause"},"response":"Paused."}),
            (["next track", "next song"],     lambda _: {"intent":"media_control","params":{"action":"next"},"response":"Next track!"}),
            (["what time", "what's the time"],lambda _: {"intent":"get_time","params":{},"response":"Let me check!"}),
            (["screenshot"],                  lambda _: {"intent":"take_screenshot","params":{},"response":"Screenshot taken!"}),
            (["lock"],                        lambda _: {"intent":"lock_screen","params":{},"response":"Locking screen!"}),
            (["sleep"],                       lambda _: {"intent":"sleep_system","params":{},"response":"Going to sleep!"}),
            (["restart", "reboot"],           lambda _: {"intent":"restart_system","params":{},"response":"Restarting now!"}),
            (["shutdown", "shut down", "power off"], lambda _: {"intent":"shutdown_system","params":{},"response":"Shutting down!"}),
        ]

        for triggers, handler in rules:
            for trigger in triggers:
                if trigger in t:
                    return handler(t)

        return {
            "intent": "general_chat",
            "params": {"message": text},
            "response": f"I'm not sure how to handle that yet — but you said: {text}",
        }

    def _rule_open(self, t):
        for kw in ["open ", "launch ", "start "]:
            if kw in t:
                app = t.split(kw, 1)[1].strip()
                return {"intent":"open_app","params":{"app":app},"response":f"Opening {app}!"}
        return {"intent":"unknown","params":{},"response":"Hmm, I didn't catch what to open."}

    def _rule_close(self, t):
        for kw in ["close ", "quit ", "exit "]:
            if kw in t:
                app = t.split(kw, 1)[1].strip()
                return {"intent":"close_app","params":{"app":app},"response":f"Closing {app}!"}
        return {"intent":"unknown","params":{},"response":"What should I close?"}

    def _rule_search(self, t):
        for kw in ["search for ", "search ", "google ", "look up "]:
            if kw in t:
                q = t.split(kw, 1)[1].strip()
                return {"intent":"web_search","params":{"query":q},"response":f"Searching for {q}!"}
        return {"intent":"unknown","params":{},"response":"What should I search for?"}

    # ------------------------------------------------------------------ #
    def _safe_parse_json(self, raw: str) -> dict:
        try:
            # Strip markdown fences if present
            clean = raw.strip().strip("```json").strip("```").strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            logger.warning(f"Could not parse JSON: {raw[:200]}")
            return {
                "intent": "general_chat",
                "params": {"message": raw},
                "response": raw[:300] if len(raw) < 300 else "I had trouble understanding that, could you say it again?",
            }
