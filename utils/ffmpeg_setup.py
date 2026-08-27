"""
FRIDAY ffmpeg setup
Whisper shells out to a bare `ffmpeg` command to decode audio. Rather than rely
on a system-wide ffmpeg install (the cause of the [WinError 2] transcription
failures), we bundle one via imageio-ffmpeg and expose it on PATH under the
plain name `ffmpeg` that Whisper expects.
"""

import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("FRIDAY.ffmpeg")


def ensure_ffmpeg_on_path() -> bool:
    """Make a bundled ffmpeg binary available as `ffmpeg` on PATH.

    Returns True if ffmpeg is available afterwards, False otherwise.
    Safe to call multiple times — it is idempotent.
    """
    # Already resolvable by its plain name? Nothing to do.
    if shutil.which("ffmpeg"):
        return True

    try:
        import imageio_ffmpeg
    except ImportError:
        logger.warning(
            "imageio-ffmpeg not installed — Whisper may fail to decode audio. "
            "Run: pip install imageio-ffmpeg"
        )
        return False

    try:
        src = Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception as e:  # binary download/lookup failed
        logger.warning(f"Could not locate bundled ffmpeg: {e}")
        return False

    # imageio's binary has a versioned filename (e.g. ffmpeg-win-x86_64-v7.1.exe),
    # but Whisper invokes the bare name `ffmpeg`. Copy it once into a cache dir
    # under the expected name and prepend that dir to PATH.
    target_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    cache_dir = Path.home() / ".friday" / "bin"
    target = cache_dir / target_name

    try:
        if not target.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            if os.name != "nt":
                target.chmod(0o755)
    except Exception as e:
        logger.warning(f"Could not stage ffmpeg into {cache_dir}: {e}")
        return False

    os.environ["PATH"] = str(cache_dir) + os.pathsep + os.environ.get("PATH", "")
    logger.info(f"ffmpeg ready: {target}")
    return True
