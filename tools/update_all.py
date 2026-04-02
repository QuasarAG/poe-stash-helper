#!/usr/bin/env python3
"""
tools/update_all.py  --  Rebuild ALL local databases.

Usage:
    python tools/update_all.py                  full rebuild
    python tools/update_all.py --force-fetch    bypass 24h cache
    python tools/update_all.py --mods           mod tiers only
    python tools/update_all.py --bases          base items only
    python tools/update_all.py --dry            dry-run, no writes
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import UpdateMode
from services.data_update_service import run_update


def _resolve_mode(only_bases: bool, only_mods: bool) -> UpdateMode:
    if only_bases and only_mods:
        raise ValueError("Choose only one of --bases or --mods.")
    if only_bases:
        return UpdateMode.BASES
    if only_mods:
        return UpdateMode.MODS
    return UpdateMode.ALL


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild generated RePoE/PoB data files.")
    parser.add_argument("--force-fetch", action="store_true", help="Bypass 24h cache")
    parser.add_argument("--bases", action="store_true", help="Rebuild base items only")
    parser.add_argument("--mods", action="store_true", help="Rebuild mod tiers only")
    parser.add_argument("--dry", action="store_true", help="Dry-run, no writes")
    args = parser.parse_args()

    mode = _resolve_mode(only_bases=args.bases, only_mods=args.mods)

    print("=" * 60)
    print("PoE Stash Helper -- Full Database Rebuild")
    print("=" * 60)

    try:
        result = run_update(mode=mode, dry_run=args.dry, force_fetch=args.force_fetch)
    except Exception as error:
        import traceback

        traceback.print_exc()
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  ERROR -- {error}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    any_written = False
    if result.bases is not None:
        status = "OK" if result.bases.get("ok") else "ERROR"
        print(f"  Base items: {status}")
        any_written = any_written or bool(result.bases.get("written"))
    if result.mods is not None:
        status = "OK" if result.mods.get("ok") else "ERROR"
        print(f"  Mod tiers:  {status}")
        any_written = any_written or bool(result.mods.get("written"))

    print()
    if args.dry:
        print("  (DRY RUN -- no files were written)")
    elif any_written:
        print("  All done. Restart the app to load the new data.")
    else:
        print("  Done.")


if __name__ == "__main__":
    main()
