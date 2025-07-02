#!/usr/bin/env python3
"""
Check Catalog Status - Avoid Redundant Conversions

This script checks if CSV data has already been converted to catalog format
and whether re-conversion is necessary based on file timestamps.

Usage:
    python scripts/check_catalog_status.py --config <config.yaml>
    python scripts/check_catalog_status.py --source-csv <path> --catalog-path <path>
"""

import argparse
import os
import sys
from datetime import datetime
from glob import glob
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from utils.data_adapters.conversion_config import ConverterConfig  # noqa: E402


def check_catalog_exists(catalog_path: str) -> bool:
    """Check if catalog directory exists and contains data."""
    path = Path(catalog_path)
    if not path.exists():
        return False

    # Check for parquet files
    parquet_files = list(path.rglob("*.parquet"))
    return len(parquet_files) > 0


def get_csv_modification_times(csv_pattern: str) -> dict:
    """Get modification times for all CSV files matching the pattern."""
    csv_files = glob(csv_pattern)
    mod_times = {}

    for csv_file in csv_files:
        if os.path.exists(csv_file):
            mod_time = os.path.getmtime(csv_file)
            mod_times[csv_file] = datetime.fromtimestamp(mod_time)

    return mod_times


def get_catalog_modification_time(catalog_path: str) -> datetime | None:
    """Get the most recent modification time of catalog files."""
    path = Path(catalog_path)
    if not path.exists():
        return None

    parquet_files = list(path.rglob("*.parquet"))
    if not parquet_files:
        return None

    # Get the most recent modification time
    latest_time = max(os.path.getmtime(f) for f in parquet_files)
    return datetime.fromtimestamp(latest_time)


def parse_data_catalog_md() -> dict:
    """Parse DATA_CATALOG.md to extract existing conversions."""
    catalog_file = Path("DATA_CATALOG.md")
    if not catalog_file.exists():
        return {}

    conversions = {}
    try:
        with open(catalog_file, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Extract source CSV pattern from header
        lines = content.split("\n")
        for line in lines:
            if line.startswith("**Source CSV Pattern**"):
                # Extract catalog info - this is a simple parser
                # In a real implementation, you'd want more robust parsing
                pass

        # For now, return empty dict - this would be enhanced to parse the table
        return conversions

    except Exception as e:
        print(f"Warning: Could not parse DATA_CATALOG.md: {e}")
        return {}


def check_conversion_needed(config: ConverterConfig) -> tuple[bool, str]:
    """
    Check if conversion is needed based on CSV and catalog timestamps.

    Returns:
        (needs_conversion: bool, reason: str)
    """

    # Check if catalog exists
    if not check_catalog_exists(config.destination_catalog):
        return True, f"Catalog does not exist at {config.destination_catalog}"

    # Get CSV modification times
    csv_mod_times = get_csv_modification_times(config.source_csv)
    if not csv_mod_times:
        return False, f"No CSV files found matching pattern: {config.source_csv}"

    # Get catalog modification time
    catalog_mod_time = get_catalog_modification_time(config.destination_catalog)
    if catalog_mod_time is None:
        return True, "Catalog exists but contains no data files"

    # Check if any CSV is newer than catalog
    latest_csv_time = max(csv_mod_times.values())
    if latest_csv_time > catalog_mod_time:
        csv_file = [f for f, t in csv_mod_times.items() if t == latest_csv_time][0]
        return (
            True,
            f"CSV file {csv_file} ({latest_csv_time}) is newer than catalog ({catalog_mod_time})",
        )

    return (
        False,
        f"Catalog is up-to-date (catalog: {catalog_mod_time}, latest CSV: {latest_csv_time})",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Check if CSV to Parquet conversion is needed"
    )
    parser.add_argument("--config", help="Path to conversion config YAML file")
    parser.add_argument(
        "--source-csv", help="Source CSV pattern (alternative to config)"
    )
    parser.add_argument(
        "--catalog-path", help="Catalog destination path (alternative to config)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.config:
        config = ConverterConfig.from_yaml(args.config)
    elif args.source_csv and args.catalog_path:
        config = ConverterConfig(
            source_csv=args.source_csv,
            destination_catalog=args.catalog_path,
            destination_meta=args.catalog_path + "_meta",
        )
    else:
        print(
            "Error: Must provide either --config or both --source-csv and --catalog-path"
        )
        sys.exit(1)

    print(f"🔍 Checking conversion status for: {config.source_csv}")
    print(f"📁 Target catalog: {config.destination_catalog}")
    print()

    # Check if conversion is needed
    needs_conversion, reason = check_conversion_needed(config)

    if needs_conversion:
        print("❌ CONVERSION NEEDED")
        print(f"   Reason: {reason}")
        print()
        print("💡 To convert, run:")
        if args.config:
            print(
                f"   python scripts/data_import/csv_to_parquet_converter.py --config {args.config}"
            )
        else:
            print(
                "   python scripts/data_import/csv_to_parquet_converter.py --config <your_config.yaml>"
            )
        sys.exit(1)
    else:
        print("✅ CONVERSION NOT NEEDED")
        print(f"   Reason: {reason}")
        print()
        print("📊 Catalog is ready to use!")

        if args.verbose:
            # Show catalog contents
            csv_files = glob(config.source_csv)
            print(f"\n📋 Source CSV files ({len(csv_files)}):")
            for csv_file in csv_files:
                mod_time = datetime.fromtimestamp(os.path.getmtime(csv_file))
                print(f"   {csv_file} (modified: {mod_time})")

            catalog_mod_time = get_catalog_modification_time(config.destination_catalog)
            print(f"\n📦 Catalog last updated: {catalog_mod_time}")

        sys.exit(0)


if __name__ == "__main__":
    main()
