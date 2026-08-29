"""
FRIDAY HUD server — serves the holographic web UI and pushes live state to it.

- HTTP (stdlib) serves ui/index.html on http://127.0.0.1:<http_port>
- WebSocket (websockets) pushes events {type, state, text} to the browser and
  receives {"type":"activate"} when the user clicks the core to talk.

The voice loop (a normal thread) calls emit(...) which is marshalled onto the
websocket asyncio loop safely.
"""
import os
import json
import asyncio
import threading
import functools
import http.server
import socketserver
import logging
import webbrowser

logger = logging.getLogger("FRIDAY.UI")
HERE = os.path.dirname(os.path.abspath(__file__))


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # don't spam the console with request logs


class UIServer:
    def __init__(self, http_port: int = 8760, ws_port: int = 8761):
        self.http_port = http_port
        self.ws_port   = ws_port
        self._clients  = set()
        self._loop     = None
        self._state    = "standby"
        self._activate = threading.Event()

    # ---- lifecycle ---------------------------------------------------- #
    def start(self):
        threading.Thread(target=self._run_http, daemon=True).start()
        threading.Thread(target=self._run_ws,   daemon=True).start()
        logger.info(f"HUD at http://127.0.0.1:{self.http_port}  (ws:{self.ws_port})")

    def open_browser(self):
        try:
            webbrowser.open(f"http://127.0.0.1:{self.http_port}")
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")

    # ---- HTTP static -------------------------------------------------- #
    def _run_http(self):
        handler = functools.partial(_QuietHandler, directory=HERE)
        try:
            with socketserver.ThreadingTCPServer(("127.0.0.1", self.http_port), handler) as httpd:
                httpd.serve_forever()
        except OSError as e:
            logger.warning(f"HUD HTTP server error: {e}")

    # ---- WebSocket ---------------------------------------------------- #
    def _run_ws(self):
        try:
            import websockets  # noqa
        except ImportError:
            logger.warning("websockets not installed — run: pip install websockets")
            return
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._ws_main())
        self._loop.run_forever()

    async def _ws_main(self):
        import websockets
        await websockets.serve(self._handler, "127.0.0.1", self.ws_port)

    async def _handler(self, ws):
        self._clients.add(ws)
        try:
            await ws.send(json.dumps({"type": "state", "state": self._state}))
            async for msg in ws:
                try:
                    data = json.loads(msg)
                except (ValueError, TypeError):
                    continue
                if data.get("type") == "activate":
                    self._activate.set()
        except Exception:
            pass
        finally:
            self._clients.discard(ws)

    # ---- emit (called from the voice thread) -------------------------- #
    def emit(self, **event):
        if "state" in event:
            self._state = event["state"]
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(event), self._loop)

    async def _broadcast(self, event):
        if not self._clients:
            return
        data = json.dumps(event)
        await asyncio.gather(*(self._safe_send(c, data) for c in list(self._clients)),
                             return_exceptions=True)

    async def _safe_send(self, ws, data):
        try:
            await ws.send(data)
        except Exception:
            self._clients.discard(ws)

    # ---- click-to-talk ------------------------------------------------ #
    def consume_activate(self) -> bool:
        """True (once) if the user clicked the core in the browser."""
        if self._activate.is_set():
            self._activate.clear()
            return True
        return False
