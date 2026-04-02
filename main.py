from __future__ import annotations

"""
main.py
─────────────────────────────────────────────────────────────────────────────
Tiny application entry point.

This file is intentionally small now.

WHY THIS IS BETTER
    A beginner opening main.py should quickly understand how the program starts.
    It should not immediately drop them into hundreds of lines of window,
    thread, tray, and scan logic.

CURRENT STARTUP FLOW
    1. enable Qt high-DPI support
    2. create QApplication
    3. load config.json
    4. create the main application controller
    5. start the Qt event loop
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import config
from controllers.app_controller import AppController


def main() -> None:
    """Create the Qt application and hand control to AppController."""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    app = QApplication(sys.argv)
    app.setApplicationName("PoE Stash Helper")
    app.setQuitOnLastWindowClosed(False)

    config.load_config()

    # Keep a reference so the controller is not garbage-collected.
    controller = AppController(app)
    _ = controller

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
