from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeStatSummary:
    """Flat representation of one official trade-stat entry."""

    id: str
    label: str
    group: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label, "group": self.group}

    @classmethod
    def from_dict(cls, payload: dict) -> "TradeStatSummary":
        return cls(
            id=payload.get("id", ""),
            label=payload.get("label", ""),
            group=payload.get("group", ""),
        )
