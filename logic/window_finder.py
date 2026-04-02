from __future__ import annotations
"""
logic/window_finder.py — Locate the Path of Exile game window on screen
and compute stash grid screen coordinates.

Windows: uses win32gui
Linux:   uses xdotool (subprocess)
macOS:   uses Quartz (limited — PoE only runs on Windows natively)
"""

import platform
import subprocess
from typing import Optional

from config import get

SYSTEM = platform.system()

_POE_TITLES = ["Path of Exile", "Path of Exile 2"]


def find_poe_window() -> Optional[tuple[int, int, int, int]]:
    """
    Returns (left, top, right, bottom) of the PoE window in screen pixels.
    Returns None if the window is not found.
    """
    if SYSTEM == "Windows":
        return _find_windows()
    elif SYSTEM == "Linux":
        return _find_linux()
    return None


def get_poe_hwnd() -> Optional[int]:
    """Return the HWND of the PoE window, or None if not found / not Windows."""
    if SYSTEM != "Windows":
        return None
    try:
        import win32gui
        result = None

        def _cb(hwnd, _):
            nonlocal result
            title = win32gui.GetWindowText(hwnd)
            if any(t in title for t in _POE_TITLES) and win32gui.IsWindowVisible(hwnd):
                result = hwnd

        win32gui.EnumWindows(_cb, None)
        return result
    except Exception:
        return None


def is_poe_minimized() -> bool:
    """Return True if the PoE window exists AND is currently minimized (iconic).

    Returns False when PoE is not running or when not on Windows.
    """
    if SYSTEM != "Windows":
        return False
    try:
        import win32gui
        hwnd = get_poe_hwnd()
        if hwnd is None:
            return False
        return bool(win32gui.IsIconic(hwnd))
    except Exception:
        return False


def _find_windows() -> Optional[tuple[int, int, int, int]]:
    try:
        import win32gui
        result = None

        def enum_cb(hwnd, _):
            nonlocal result
            title = win32gui.GetWindowText(hwnd)
            if any(t in title for t in _POE_TITLES) and win32gui.IsWindowVisible(hwnd):
                rect = win32gui.GetClientRect(hwnd)
                # Convert client rect to screen coords
                pt = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
                result = (pt[0], pt[1],
                          pt[0] + rect[2] - rect[0],
                          pt[1] + rect[3] - rect[1])

        win32gui.EnumWindows(enum_cb, None)
        return result
    except ImportError:
        print("[WindowFinder] pywin32 not installed — window auto-detection disabled")
        return None
    except Exception as e:
        print(f"[WindowFinder] Error: {e}")
        return None


def _find_linux() -> Optional[tuple[int, int, int, int]]:
    try:
        wid = subprocess.check_output(
            ["xdotool", "search", "--name", "Path of Exile"],
            timeout=3
        ).decode().strip().split("\n")[0]
        geo = subprocess.check_output(
            ["xdotool", "getwindowgeometry", "--shell", wid],
            timeout=3
        ).decode()
        data = {}
        for line in geo.strip().split("\n"):
            k, _, v = line.partition("=")
            data[k.strip()] = int(v.strip())
        l = data.get("X", 0)
        t = data.get("Y", 0)
        w = data.get("WIDTH", 1920)
        h = data.get("HEIGHT", 1080)
        return (l, t, l + w, t + h)
    except Exception:
        return None


# ─── Grid coordinate mapper ───────────────────────────────────────────────

def cell_screen_rect(item_x: int, item_y: int, item_w: int, item_h: int,
                     window_rect: tuple) -> tuple[int, int, int, int]:
    """
    Convert stash grid coordinates (item.x, item.y, item.w, item.h)
    to absolute screen pixel rect (left, top, right, bottom).

    The stash panel is on the LEFT side of the screen in PoE.
    Geometry constants from config (tunable per resolution).
    """
    cfg = get("stash_grid") or {}
    win_left  = window_rect[0]
    win_top   = window_rect[1]
    win_h     = window_rect[3] - window_rect[1]

    # Scale cell size to current window height (designed for 1080p)
    scale = win_h / 1080.0
    cell  = cfg.get("cell_size", 52) * scale
    ox    = cfg.get("origin_x",  14) * scale + win_left
    oy    = cfg.get("origin_y", 134) * scale + win_top

    left  = int(ox + item_x * cell)
    top   = int(oy + item_y * cell)
    right = int(left + item_w * cell)
    bottom= int(top  + item_h * cell)
    return (left, top, right, bottom)
