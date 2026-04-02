from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.enums import StashTabType


@dataclass(frozen=True)
class StashTabSummary:
    """Small, stable representation of a stash tab shown in the interface."""

    name: str
    id: str
    type: StashTabType | str = StashTabType.NORMAL
    index: int = -1

    @classmethod
    def from_api_dict(cls, payload: dict[str, Any]) -> "StashTabSummary":
        raw_type = payload.get("type", StashTabType.NORMAL.value)
        try:
            stash_type: StashTabType | str = StashTabType(raw_type)
        except ValueError:
            stash_type = raw_type

        return cls(
            name=payload.get("name", "?"),
            id=payload.get("id", str(payload.get("index", ""))),
            type=stash_type,
            index=int(payload.get("index", -1) or -1),
        )

    @property
    def type_value(self) -> str:
        return self.type.value if isinstance(self.type, StashTabType) else str(self.type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "id": self.id,
            "type": self.type_value,
            "index": self.index,
        }


def coerce_stash_tab_summary(value: Any) -> StashTabSummary:
    """Accept either a summary object or an old-style dict and normalize it."""
    if isinstance(value, StashTabSummary):
        return value
    if isinstance(value, dict):
        return StashTabSummary.from_api_dict(value)
    raise TypeError(f"Unsupported stash tab value: {type(value).__name__}")
