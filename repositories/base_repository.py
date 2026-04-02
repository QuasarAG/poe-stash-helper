from __future__ import annotations

"""
repositories/base_repository.py
─────────────────────────────────────────────────────────────────────────────
Single source of truth for generated base-item data.

WHY THIS FILE EXISTS
    Earlier in the project, more than one module loaded `data/base_types.json`
    directly. That created a duplication problem:

        - one module could build one lookup shape
        - another module could build a slightly different lookup shape
        - after a database update, one part of the app might refresh while
          another part still used older in-memory data

    A repository fixes that by giving the project one place that *owns* the
    loading and interpretation of that file.

BEGINNER MENTAL MODEL
    Think of a repository as:
        "the official librarian for one kind of data"

    Instead of many parts of the app walking into the file system and reading
    the same JSON file themselves, they ask the librarian for what they need.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass
class WeaponGroup:
    """
    Friendly structure for grouped weapon data shown in the user interface.

    label
        Human-readable group title such as a weapon family name.

    attributes
        Distinct stat strings used by the UI to build attribute filter sections.

    bases
        Raw base entries for that group.

    is_flat
        Some groups are displayed as one flat list instead of by sub-type.
    """

    label: str
    attributes: list[str]
    bases: list[dict]
    is_flat: bool = False


class BaseRepository:
    """
    Repository that loads and serves base-type data from `data/base_types.json`.

    This class keeps both:
        - the original raw JSON structure
        - several precomputed helper structures used by the UI and parser

    Precomputing the helper structures here is useful because it means the rest
    of the application can stay simpler and does not need to repeat the same
    transformation logic every time.
    """

    def __init__(self, data_path: Path | None = None):
        self._data_path = data_path or (
            Path(__file__).resolve().parent.parent / "data" / "base_types.json"
        )

        # The fields below are filled by reload(). They are stored on the
        # repository instance so other modules can reuse the same in-memory data.
        self._raw: dict[str, Any] = {}
        self.base_types: list[dict] = []
        self.weapon_groups_main: list[dict] = []
        self.weapon_groups_off: list[dict] = []
        self.weapon_groups_quiver: list[dict] = []
        self.stat_attributes: dict = {}
        self.slot_attributes: dict = {}
        self.slots_no_attribute: set[str] = set()
        self.slots_weapon_type: set[str] = set()
        self.base_slot_lookup: dict[str, str] = {}
        self.reload()

    def _load_raw(self) -> dict[str, Any]:
        """Read the generated JSON file from disk."""
        with open(self._data_path, encoding="utf-8") as file_handle:
            return json.load(file_handle)

    def reload(self) -> None:
        """
        Reload the JSON file and rebuild all derived helper structures.

        This method is especially useful after the external RePoE update step
        rewrites `base_types.json` while the application is already running.
        """
        self._raw = self._load_raw()
        self.base_types = self._build_base_types(self._raw)
        self.weapon_groups_main = self._build_weapon_groups(self._raw.get("WEAPONS", {}))
        self.weapon_groups_off = self._build_offhand_groups(self._raw.get("OFF_HAND", {}))
        self.weapon_groups_quiver = []

        meta = self._raw.get("META", {})
        self.stat_attributes = meta.get("STAT_ATTRIBUTES", {})
        self.slot_attributes = meta.get("SLOT_ATTRIBUTES", {})
        self.slots_no_attribute = set(meta.get("SLOTS_NO_ATTRIBUTE", []))
        self.slots_weapon_type = set(meta.get("SLOTS_WEAPON_TYPE", []))
        self.base_slot_lookup = self._build_base_slot_lookup(self._raw)

    @staticmethod
    def _build_base_types(raw: dict) -> list[dict]:
        """
        Flatten selected sections of the generated JSON into one base list.

        Why flatten?
            The generated file is grouped for data-generation convenience.
            The UI often needs a simple list it can filter by slot.
        """
        result: list[dict] = []

        for slot, bases in raw.get("ARMOUR", {}).items():
            for base in bases:
                result.append({**base, "slot": slot})

        for slot, bases in raw.get("ACCESSORIES", {}).items():
            if slot == "Flask":
                if isinstance(bases, dict):
                    for flask_type, flask_bases in bases.items():
                        for base in flask_bases:
                            result.append({**base, "slot": "Flask", "flask_type": flask_type})
            elif isinstance(bases, list):
                for base in bases:
                    result.append({**base, "slot": slot})

        quiver_raw = raw.get("OFF_HAND", {}).get("Quivers", [])
        if isinstance(quiver_raw, list):
            for base in quiver_raw:
                result.append({**base, "slot": "Quiver"})
        elif isinstance(quiver_raw, dict):
            for _, weapon_bases in quiver_raw.items():
                for base in weapon_bases:
                    result.append({**base, "slot": "Quiver"})

        return result

    @staticmethod
    def _build_weapon_groups(section: dict) -> list[dict]:
        """Build grouped main-hand weapon sections for the Item Base UI."""
        groups = []
        for group_label, weapon_types in section.items():
            if not isinstance(weapon_types, dict):
                continue

            bases = []
            for weapon_type, weapon_bases in weapon_types.items():
                for base in weapon_bases:
                    bases.append({**base, "slot": "Main Hand", "wtype": weapon_type})

            attributes = sorted({base.get("stats", "") for base in bases if base.get("stats")})
            groups.append({"label": group_label, "attributes": attributes, "bases": bases})
        return groups

    @staticmethod
    def _build_offhand_groups(section: dict) -> list[dict]:
        """Build grouped off-hand sections for shields, foci, quivers, and similar items."""
        groups = []
        for group_label, content in section.items():
            if group_label == "Quivers":
                if isinstance(content, list):
                    raw_bases = content
                elif isinstance(content, dict):
                    raw_bases = [base for weapon_bases in content.values() for base in weapon_bases]
                else:
                    continue

                bases = [{**base, "slot": "Off-hand"} for base in raw_bases]
                groups.append({
                    "label": "Quivers",
                    "attributes": [],
                    "bases": bases,
                    "is_flat": True,
                })
            elif isinstance(content, dict):
                bases = []
                for weapon_type, weapon_bases in content.items():
                    for base in weapon_bases:
                        bases.append({**base, "slot": "Off-hand", "wtype": weapon_type})
                attributes = sorted({base.get("stats", "") for base in bases if base.get("stats")})
                groups.append({"label": group_label, "attributes": attributes, "bases": bases})
        return groups

    @staticmethod
    def _build_base_slot_lookup(raw: dict) -> dict[str, str]:
        """
        Build a name -> slot lookup.

        This lookup is one of the main reasons the repository exists.
        Item parsing code needs a quick answer to the question:
            "Given this base item name, which slot does it belong to?"
        """
        lookup: dict[str, str] = {}

        for slot, bases in raw.get("ARMOUR", {}).items():
            for base in bases:
                lookup[base["name"]] = slot

        for slot, bases in raw.get("ACCESSORIES", {}).items():
            if isinstance(bases, dict):
                for base_group in bases.values():
                    for base in base_group:
                        lookup[base["name"]] = "Flask"
            elif isinstance(bases, list):
                for base in bases:
                    lookup[base["name"]] = slot

        for weapon_group in raw.get("WEAPONS", {}).values():
            if isinstance(weapon_group, dict):
                for weapon_bases in weapon_group.values():
                    for base in weapon_bases:
                        lookup[base["name"]] = "Main Hand"

        for offhand_group in raw.get("OFF_HAND", {}).values():
            if isinstance(offhand_group, list):
                for base in offhand_group:
                    lookup[base["name"]] = "Off-hand"
            elif isinstance(offhand_group, dict):
                for weapon_bases in offhand_group.values():
                    if isinstance(weapon_bases, list):
                        for base in weapon_bases:
                            lookup[base["name"]] = "Off-hand"

        return lookup

    def get_slot_for_base_type(self, base_type: str) -> str | None:
        """Return the item slot for a base type name, if known."""
        return self.base_slot_lookup.get(base_type)

    def get_attributes_for_slot(self, slot: str) -> list[str]:
        """
        Return the attribute categories available for one slot.

        Some slots have explicit metadata in the generated file.
        Others are derived from the flattened base list.
        """
        if slot in self.slot_attributes and self.slot_attributes[slot]:
            return self.slot_attributes[slot]
        if slot in self.slots_no_attribute:
            return ["NONE"]

        seen: list[str] = []
        for base in self.base_types:
            if base["slot"] == slot:
                attr = base.get("stats", "NONE") or "NONE"
                if attr not in seen:
                    seen.append(attr)
        return seen or ["NONE"]

    def get_flask_groups(self) -> dict[str, list[dict]]:
        """Return flask bases grouped by flask subtype for the Item Base panel."""
        groups: dict[str, list[dict]] = {
            "Life Flask": [],
            "Mana Flask": [],
            "Hybrid Flask": [],
            "Utility Flask": [],
        }
        for base in self.base_types:
            if base.get("slot") != "Flask":
                continue
            flask_type = base.get("flask_type", "Utility Flask") or "Utility Flask"
            groups.setdefault(flask_type, []).append(base)
        for flask_type in groups:
            groups[flask_type].sort(key=lambda base: base.get("req_ilvl", 0))
        return groups

    def get_bases_for_slot_attribute(self, slot: str, attr: str) -> list[dict]:
        """Return sorted bases for one slot + attribute combination."""
        target = attr if attr != "NONE" else None
        return sorted(
            (
                base
                for base in self.base_types
                if base["slot"] == slot and (base.get("stats") or "NONE") == (target or "NONE")
            ),
            key=lambda base: base.get("req_ilvl", 0),
        )


# Keep one default repository instance for the current application run.
_default_repository = BaseRepository()


def get_default_base_repository() -> BaseRepository:
    """Return the shared repository instance used by the rest of the application."""
    return _default_repository
