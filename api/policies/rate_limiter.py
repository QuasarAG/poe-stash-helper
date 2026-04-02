from __future__ import annotations
"""Thread-safe request pacing for the official Path of Exile API.

WHY THIS FILE EXISTS
    The Path of Exile developer documentation says applications must respect the
    dynamic rate-limit headers returned by the API and back off when limited.
    Public desktop clients share limits with other public clients, so being
    deliberately conservative is the safest choice.
"""

import threading
import time
from collections import deque

from config import API


class RateLimiter:
    """Simple sliding-window limiter with Retry-After support."""

    def __init__(self, requests: int, window_sec: float):
        self._max_requests = max(1, int(requests))
        self._window = max(0.1, float(window_sec))
        self._timestamps: deque[float] = deque()
        self._retry_after_deadline = 0.0
        self._lock = threading.Lock()

    def wait_for_slot(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._retry_after_deadline > now:
                time.sleep(self._retry_after_deadline - now)

            cutoff = time.monotonic() - self._window
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._max_requests:
                oldest = self._timestamps[0]
                sleep_for = (oldest + self._window) - time.monotonic() + 0.05
                if sleep_for > 0:
                    time.sleep(sleep_for)

            if self._timestamps:
                elapsed = time.monotonic() - self._timestamps[-1]
                min_delay = API["min_request_delay"]
                if elapsed < min_delay:
                    time.sleep(min_delay - elapsed)

            self._timestamps.append(time.monotonic())

    def update_from_headers(self, headers: dict) -> None:
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                self._retry_after_deadline = time.monotonic() + float(retry_after)
            except ValueError:
                pass

        limit_header = headers.get("X-Rate-Limit-Account", "")
        state_header = headers.get("X-Rate-Limit-Account-State", "")
        if not limit_header or not state_header:
            return
        try:
            rules = [entry.split(":") for entry in limit_header.split(",")]
            states = [entry.split(":") for entry in state_header.split(",")]
            for rule, state in zip(rules, states):
                max_hits = int(rule[0])
                period = float(rule[1])
                current_hits = int(state[0])
                if current_hits >= max_hits * 0.8:
                    self._window = period
                    self._max_requests = max(1, max_hits - 5)
        except (ValueError, IndexError):
            return
