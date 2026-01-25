#!/usr/bin/env python
"""Migration script to rename data files from ISIN to ticker-based naming.

This script:
1. Reads all {ISIN}_data.json files
2. Extracts the ticker symbol from each file
3. Renames the file to {TICKER}_data.json
4. Handles duplicates (multiple ISINs for same ticker)
"""

import json
import shutil
from pathlib import Path


def migrate_data_files(data_dir: Path | None = None, dry_run: bool = True) -> None:
    """Migrate data files from ISIN to ticker-based naming.

    Args:
        data_dir: Directory containing *_data.json files
        dry_run: If True, only print what would be done without making changes
    """
    if data_dir is None:
        data_dir = Path("data/stock_data")

    if not data_dir.exists():
        print(f"Data directory does not exist: {data_dir}")
        return

    # Track migrations and potential conflicts
    migrations: dict[str, list[Path]] = {}  # ticker -> list of source files

    # First pass: identify all files and their tickers
    for data_file in sorted(data_dir.glob("*_data.json")):
        filename = data_file.stem  # e.g., "US67066G1040_data" or "UNKNOWN-NVDA_data"

        # Skip files that are already ticker-based (no ISIN prefix)
        # ISINs are 12 chars, UNKNOWN-{ticker} or actual ISINs
        prefix = filename.replace("_data", "")

        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"ERROR: Could not read {data_file}: {e}")
            continue

        ticker = data.get("ticker") or data.get("symbol")
        if not ticker:
            print(f"WARNING: No ticker found in {data_file}, skipping")
            continue

        ticker = ticker.upper()

        # Check if this file is already ticker-named
        if prefix == ticker:
            print(f"SKIP: {data_file.name} already ticker-based")
            continue

        if ticker not in migrations:
            migrations[ticker] = []
        migrations[ticker].append(data_file)

    # Second pass: perform migrations
    for ticker, source_files in sorted(migrations.items()):
        target_file = data_dir / f"{ticker}_data.json"

        if len(source_files) > 1:
            # Multiple ISINs for same ticker - use the most recent one
            print(f"\nWARNING: Multiple files for {ticker}:")
            newest_file = None
            newest_time = None
            for sf in source_files:
                mtime = sf.stat().st_mtime
                print(f"  - {sf.name} (modified: {mtime})")
                if newest_time is None or mtime > newest_time:
                    newest_time = mtime
                    newest_file = sf
            source_file = newest_file
            print(f"  Using newest: {source_file.name}")
        else:
            source_file = source_files[0]

        if dry_run:
            print(f"WOULD RENAME: {source_file.name} -> {target_file.name}")
        else:
            if target_file.exists() and target_file != source_file:
                # Backup existing file
                backup_file = data_dir / f"{ticker}_data.json.bak"
                print(f"BACKUP: {target_file.name} -> {backup_file.name}")
                shutil.copy2(target_file, backup_file)

            print(f"RENAME: {source_file.name} -> {target_file.name}")
            source_file.rename(target_file)

            # Delete other files for the same ticker
            for sf in source_files:
                if sf != source_file and sf.exists():
                    print(f"DELETE: {sf.name} (duplicate)")
                    sf.unlink()


def migrate_state_files(state_dir: Path | None = None, dry_run: bool = True) -> None:
    """Remove ISIN field from state files (holdings and trades).

    Args:
        state_dir: Directory containing portfolio state JSON files
        dry_run: If True, only print what would be done without making changes
    """
    if state_dir is None:
        state_dir = Path("data/state")

    if not state_dir.exists():
        print(f"State directory does not exist: {state_dir}")
        return

    for state_file in sorted(state_dir.glob("*.json")):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"ERROR: Could not read {state_file}: {e}")
            continue

        modified = False

        # Remove isin from holdings
        for holding in data.get("holdings", []):
            if "isin" in holding:
                if dry_run:
                    print(f"WOULD REMOVE: {state_file.name} holdings[].isin")
                else:
                    del holding["isin"]
                modified = True

        # Remove isin from trades
        for trade in data.get("trades", []):
            if "isin" in trade:
                if dry_run:
                    print(f"WOULD REMOVE: {state_file.name} trades[].isin")
                else:
                    del trade["isin"]
                modified = True

        if modified and not dry_run:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"UPDATED: {state_file.name}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate data files from ISIN to ticker-based naming")
    parser.add_argument("--apply", action="store_true", help="Actually perform the migration (default is dry-run)")
    parser.add_argument("--data-dir", type=Path, default=Path("data/stock_data"), help="Stock data directory")
    parser.add_argument("--state-dir", type=Path, default=Path("data/state"), help="State directory")
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        print("=== DRY RUN MODE (use --apply to perform migration) ===\n")
    else:
        print("=== APPLYING MIGRATION ===\n")

    print("--- Migrating data files ---")
    migrate_data_files(args.data_dir, dry_run=dry_run)

    print("\n--- Migrating state files ---")
    migrate_state_files(args.state_dir, dry_run=dry_run)

    print("\nDone!")
