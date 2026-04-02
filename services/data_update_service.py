"""services/data_update_service.py
─────────────────────────────────────────────────────────────────────────────
Reusable service for rebuilding generated game data.

WHY THIS FILE EXISTS
    Before the Phase 2 refactor, the UI updater and the command-line update
    script both tried to run the builder scripts by pretending to be a terminal
    process. That led to fragile patterns such as rewriting `sys.argv`.

    This service is the clean middle layer:
        UI button or Qt worker  ->  this service  ->  builder modules
        CLI script             ->  this service  ->  builder modules

BEGINNER RULE OF THUMB
    If two different entry points need the same workflow, put that workflow in
    a normal reusable function, and let the entry points stay thin.
"""

from __future__ import annotations

from dataclasses import dataclass

from models import UpdateMode
from tools import build_base_db, build_mod_db


@dataclass
class UpdateRunResult:
    """
    Structured result returned by run_update().

    Using a dataclass is nicer than returning a loose tuple because the meaning
    of each field stays obvious to a beginner reading the code later.
    """

    ok: bool
    mode: UpdateMode
    bases: dict | None = None
    mods: dict | None = None

    def summary_message(self) -> str:
        """Return a short human-friendly status line for the UI."""
        if not self.ok:
            return "✗  Database update failed."
        if self.mode == UpdateMode.BASES:
            return "✓  Base items rebuilt from RePoE."
        if self.mode == UpdateMode.MODS:
            return "✓  Mod tiers rebuilt from RePoE."
        return "✓  Base items and mod tiers rebuilt from RePoE."


def run_update(
    *,
    mode: UpdateMode,
    dry_run: bool = False,
    force_fetch: bool = False,
) -> UpdateRunResult:
    """
    Run one or both data builders and return structured results.

    mode
        "bases"  -> rebuild only base item data
        "mods"   -> rebuild only mod data
        "all"    -> rebuild both

    dry_run
        Optional builder flag for inspection/testing workflows.

    force_fetch
        Ignore warm cache data and fetch fresh remote data where the builders
        support it.
    """
    mode = UpdateMode(mode)

    bases_result = None
    mods_result = None

    if mode in {UpdateMode.BASES, UpdateMode.ALL}:
        bases_result = build_base_db.run_build(
            dry_run=dry_run,
            force_fetch=force_fetch,
        )

    if mode in {UpdateMode.MODS, UpdateMode.ALL}:
        mods_result = build_mod_db.run_build(
            dry_run=dry_run,
            force_fetch=force_fetch,
        )

    return UpdateRunResult(
        ok=True,
        mode=mode,
        bases=bases_result,
        mods=mods_result,
    )
