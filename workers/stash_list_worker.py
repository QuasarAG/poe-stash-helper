from __future__ import annotations

"""Shared background worker that fetches the player's stash-tab list.

Earlier versions of the project had two separate workers for the same HTTP
request: one used by the Account tab and one used by the application
controller. Merging them removes duplicate code and gives the stash-list
request one obvious worker home.
"""

from PyQt5.QtCore import QThread, pyqtSignal

from services.stash_service import list_stashes


class StashListWorker(QThread):
    stash_list_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, token: str, league: str):
        super().__init__()
        self.token = token
        self.league = league

    def run(self) -> None:
        try:
            tabs = list_stashes(self.league, self.token)
            self.stash_list_ready.emit(tabs)
        except Exception as error:  # pragma: no cover - defensive UI worker code
            self.error.emit(f"Could not load stash tabs. {error}")
