"""
FRIDAY desktop window — hosts the HUD in a native application window instead of
a browser tab.

Preferred: pywebview (native OS window via WebView2 on Windows).
Fallbacks: a chromeless Edge/Chrome "--app" window, then a normal browser tab.
"""
import os
import shutil
import logging
import threading
import subprocess
import webbrowser

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
    """Open the HUD as a desktop window and run FRIDAY. Blocks until it closes."""
    url = f"http://127.0.0.1:{ui.http_port}"

    # --- Preferred: native window via pywebview --------------------------- #
    try:
        import webview
        # The voice loop runs in the background; the GUI owns the main thread.
        threading.Thread(
            target=lambda: (friday.greet(), friday.run()),
            daemon=True,
        ).start()
        webview.create_window(
            "FRIDAY",
            url,
            width=1120, height=720,
            min_size=(900, 600),
            background_color="#01060F",
        )
        logger.info("Launching FRIDAY desktop window (pywebview)")
        webview.start()   # blocks on the main thread until the window is closed
        return
    except Exception as e:
        logger.warning(f"pywebview window unavailable ({e}); trying app-mode window")

    # --- Fallback: chromeless Edge/Chrome window -------------------------- #
    browser = _find_chromium()
    if browser:
        try:
            subprocess.Popen([browser, f"--app={url}", "--window-size=1120,760"])
            logger.info(f"Launched app-mode window via {os.path.basename(browser)}")
        except Exception as e:
            logger.warning(f"app-mode failed ({e}); opening a browser tab")
            webbrowser.open(url)
    else:
        webbrowser.open(url)

    # The window opened without blocking, so run the assistant here.
    friday.greet()
    friday.run()
