"""
FRIDAY Skills: Browser + Filesystem + Media + Info + Terminal
"""

import os
import shutil
import subprocess
import platform
import webbrowser
import logging
from datetime import datetime
from urllib.parse import quote_plus

logger = logging.getLogger("FRIDAY.skills")
SYSTEM = platform.system()


# ════════════════════════════════════════════════════════════════════════════
# BROWSER
# ════════════════════════════════════════════════════════════════════════════

def web_search(params: dict) -> str:
    query   = params.get("query", "")
    browser = params.get("browser", "default")
    url     = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searching for '{query}'!"

def open_url(params: dict) -> str:
    url = params.get("url", "")
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}!"
