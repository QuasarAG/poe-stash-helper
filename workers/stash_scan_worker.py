from __future__ import annotations

"""Background worker that performs one stash scan.

The worker receives a :class:`models.ScanRequest` so all scan inputs travel
through the codebase as one clearly named object instead of a long list of
loosely related arguments.
"""

import copy
import traceback as traceback_module

from PyQt5.QtCore import QThread, pyqtSignal

from logic.item_parser import ParsedItem, parse_stash_items
from logic.mod_scorer import apply_scores
from models import ScanRequest, ScanResult
from services.stash_service import get_stash


class StashScanWorker(QThread):
    items_ready = pyqtSignal(object)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    error_detail = pyqtSignal(str)

    def __init__(self, request: ScanRequest):
        super().__init__()
        self.request = ScanRequest(
            access_token=request.access_token,
            account_name=request.account_name,
            league=request.league,
            stash_id=request.stash_id,
            filters=copy.deepcopy(request.filters),
            scan_id=request.scan_id,
        )

    def run(self) -> None:
        try:
            self.status.emit("Fetching stash…")
            stash_payload = get_stash(
                self.request.league,
                self.request.stash_id,
                self.request.access_token,
            )

            parsed_items: list[ParsedItem] = parse_stash_items(stash_payload)
            item_count = len(parsed_items)

            self.status.emit(f"Scoring {item_count} items…")
            apply_scores(parsed_items, self.request.filters)

            self.items_ready.emit(
                ScanResult(items=parsed_items, scan_id=self.request.scan_id)
            )
            self.status.emit(f"Done — {item_count} items scanned.")
        except Exception as error:  # pragma: no cover - defensive UI worker code
            traceback_text = traceback_module.format_exc()
            print(f"[Scan #{self.request.scan_id}] ERROR:\n{traceback_text}")
            self.error_detail.emit(traceback_text)
            self.error.emit(
                f"Could not scan the stash tab. {type(error).__name__}: {error}"
            )
