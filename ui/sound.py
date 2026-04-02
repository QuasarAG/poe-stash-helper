from __future__ import annotations
"""
ui/sound.py — Play a short ding sound when a scan completes.
Uses winsound on Windows, afplay on macOS, paplay/aplay on Linux.
Falls back silently if nothing is available.
"""

import platform
import threading

SYSTEM = platform.system()


def play_ding():
    """Non-blocking: plays a ding in a background thread."""
    t = threading.Thread(target=_play, daemon=True)
    t.start()


def _play():
    try:
        if SYSTEM == "Windows":
            import winsound
            # MB_OK = standard system "asterisk" ding
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif SYSTEM == "Darwin":
            import subprocess
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"],
                           timeout=3, capture_output=True)
        else:  # Linux
            import subprocess
            # Try paplay (PulseAudio), fall back to aplay
            for cmd in [
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                ["aplay",  "/usr/share/sounds/freedesktop/stereo/complete.wav"],
            ]:
                try:
                    subprocess.run(cmd, timeout=3, capture_output=True)
                    return
                except FileNotFoundError:
                    continue
    except Exception:
        pass   # silent fallback — never crash the app over a sound
