"""
Launch EDITH's HUD as a desktop application window (not a browser tab).

Order of preference:
  1. pywebview  — a true native window (pip install pywebview), best "app" feel
  2. Edge/Chrome in --app mode — a chromeless application window, zero extra deps
  3. default browser — last-resort fallback
"""
import os
import shutil
import subprocess
import threading
import logging

logger = logging.getLogger("FRIDAY.App")


def _find_chromium():
    for name in ("msedge", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    for c in (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if os.path.exists(c):
            return c
    return None


def launch(friday, ui):
    """Open the HUD in a desktop window and run EDITH (blocks until it stops)."""
    url = f"http://127.0.0.1:{ui.http_port}"
    title = friday.cfg["assistant"].get("name", "EDITH")

    # 1) Native window via pywebview (blocks on the main thread when started,
    #    so the voice loop runs in a background thread).
    try:
        import webview
        webview.create_window(title, url, width=1160, height=760,
                              min_size=(900, 600), background_color="#01060f")
        threading.Thread(target=lambda: (friday.greet(), friday.run()),
                         daemon=True).start()
        logger.info("Desktop window via pywebview")
        webview.start()
        return
    except Exception as e:
        logger.info(f"pywebview not used ({e}); trying an app-mode window")

    # 2) Chromeless Edge/Chrome application window (non-blocking), voice loop
    #    then runs on the main thread as usual.
    exe = _find_chromium()
    if exe:
        try:
            subprocess.Popen([exe, f"--app={url}", "--window-size=1160,780"])
            logger.info(f"Desktop window via {os.path.basename(exe)} --app")
        except Exception as e:
            logger.warning(f"app-mode failed ({e}); opening default browser")
            ui.open_browser()
    else:
        ui.open_browser()

    friday.greet()
    friday.run()
