import requests
import logging

logger = logging.getLogger("FRIDAY.utils.network")

def is_online(url: str = "https://www.google.com", timeout: int = 3) -> bool:
    try:
        requests.get(url, timeout=timeout)
        return True
    except Exception:
        logger.info("No internet connection — running in offline mode")
        return False
