#!/usr/bin/env python3
"""
Smart CSV to Parquet Converter

This script checks if conversion is needed before running the actual conversion,
preventing redundant work and following the efficiency rules in cursor_rules.md.

Usage:
    python scripts/smart_convert.py --config <config.yaml>
    python scripts/smart_convert.py --config <config.yaml> --force
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(
        description="Smart CSV to Parquet converter with redundancy checking"
    )
    parser.add_argument(
        "--config", required=True, help="Path to conversion config YAML file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force conversion even if catalog is up-to-date",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("🧠 Smart CSV to Parquet Converter")
    print("=" * 50)

    # Step 1: Check if conversion is needed
    print("📋 Step 1: Checking if conversion is needed...")

    check_cmd = [
        sys.executable,
        "scripts/data_import/check_catalog_status.py",
        "--config",
        args.config,
    ]
    if args.verbose:
        check_cmd.append("--verbose")

    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:  # Conversion not needed
            print("✅ Catalog is already up-to-date!")
            print(result.stdout)

            if not args.force:
                print("💡 Use --force to convert anyway")
                sys.exit(0)
            else:
                print("🔧 --force flag detected, proceeding with conversion...")

        elif result.returncode == 1:  # Conversion needed
            print("❌ Conversion is needed")
            print(result.stdout)
            print("🚀 Proceeding with conversion...")

        else:  # Error in checking
            print("⚠️  Error checking catalog status:")
            print(result.stderr)
            print("🚀 Proceeding with conversion anyway...")

    except Exception as e:
        print(f"⚠️  Error running catalog check: {e}")
        print("🚀 Proceeding with conversion anyway...")

    # Step 2: Run the actual conversion
    print("\n📦 Step 2: Running CSV to Parquet conversion...")

    convert_cmd = [
        sys.executable,
        "scripts/data_import/csv_to_parquet_converter.py",
        "--config",
        args.config,
    ]

    try:
        result = subprocess.run(convert_cmd, check=True)
        print("\n✅ Conversion completed successfully!")

        # Step 3: Verify the result
        print("\n🔍 Step 3: Verifying conversion result...")
        verify_cmd = [
            sys.executable,
            "scripts/data_import/check_catalog_status.py",
            "--config",
            args.config,
            "--verbose",
        ]

        subprocess.run(verify_cmd, check=False)

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Conversion failed with exit code {e.returncode}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
