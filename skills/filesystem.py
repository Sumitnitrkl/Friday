"""
FRIDAY Skill: File System Operations
"""

import os
import shutil
import subprocess
import platform
import logging

logger = logging.getLogger("FRIDAY.skill.filesystem")
SYSTEM = platform.system()


def _expand(path: str) -> str:
    return os.path.expanduser(path)


def create(params: dict) -> str:
    path  = _expand(params.get("path", "~/Desktop/new_item"))
    ftype = params.get("type", "file")
    try:
        if ftype == "folder":
            os.makedirs(path, exist_ok=True)
            return f"Folder created at {path}!"
        else:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as f:
                f.write("")
            return f"File created at {path}!"
    except Exception as e:
        return f"Couldn't create that: {e}"


def open_file(params: dict) -> str:
    path = _expand(params.get("path", ""))
    if not os.path.exists(path):
        return f"Can't find {path}."
    try:
        if SYSTEM == "Darwin":
            subprocess.Popen(["open", path])
        elif SYSTEM == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
        return f"Opening {os.path.basename(path)}!"
    except Exception as e:
        return f"Couldn't open that: {e}"


def delete(params: dict) -> str:
    path = _expand(params.get("path", ""))
    if not os.path.exists(path):
        return f"File not found: {path}"
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return f"Deleted {os.path.basename(path)}."
    except Exception as e:
        return f"Couldn't delete that: {e}"


def move(params: dict) -> str:
    src = _expand(params.get("src", ""))
    dst = _expand(params.get("dst", ""))
    if not os.path.exists(src):
        return f"Source not found: {src}"
    try:
        shutil.move(src, dst)
        return f"Moved {os.path.basename(src)} to {dst}!"
    except Exception as e:
        return f"Couldn't move that: {e}"
