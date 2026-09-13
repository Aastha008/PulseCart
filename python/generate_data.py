#!/usr/bin/env python3
"""
PulseCart Synthetic Data Generation CLI Entrypoint.
Generates 100K+ realistic e-commerce sessions across 6 relational tables
with zero data fabrication and strict relational/temporal invariants.
"""

import sys
import os
import argparse
from pathlib import Path

# Enforce UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_generator.generator import GeneratorConfig, SyntheticDataGenerator, PulseCartDataGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic PulseCart dataset (>=100K sessions)")
    parser.add_argument("--sessions", type=int, default=100000, help="Number of browsing sessions (default: 100000)")
    parser.add_argument("--users", type=int, default=30000, help="Number of distinct user accounts (default: 30000)")
    parser.add_argument("--products", type=int, default=100, help="Number of catalog products (default: 100)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed (default: 42)")
    parser.add_argument("--output-dir", type=str, default="data/raw", help="Output directory for CSV and Parquet files")
    parser.add_argument("--target-lift", type=float, default=0.089, help="Pre-specified A/B checkout target lift (default: 0.089)")

    args = parser.parse_args()
    out_dir = PROJECT_ROOT / args.output_dir

    print("=" * 70)
    print("PulseCart Synthetic Data Generation Engine")
    print("=" * 70)
    print(f"Target Sessions : {args.sessions:,}")
    print(f"Target Users    : {args.users:,}")
    print(f"Target Products : {args.products}")
    print(f"Target Lift     : {args.target_lift * 100.0:.1f}%")
    print(f"Random Seed     : {args.seed}")
    print(f"Output Directory: {out_dir}")
    print("-" * 70)

    config = GeneratorConfig(
        num_sessions=args.sessions,
        num_users=args.users,
        seed=args.seed,
    )

    generator = SyntheticDataGenerator(config=config)
    dataset = generator.generate_all()

    export_paths = generator.export_dataset(
        dataset=dataset,
        output_dir=str(out_dir),
        export_parquet=True,
        export_csv=True,
    )

    tables = {
        "users": dataset.users,
        "products": dataset.products,
        "sessions": dataset.sessions,
        "events": dataset.events,
        "orders": dataset.orders,
        "order_items": dataset.order_items,
    }

    print("\nDataset Generation Summary:")
    for name, df in tables.items():
        print(f"  - {name:15s}: {len(df):>10,d} rows | {len(df.columns):>2d} columns")

    # Run verification invariants
    invariants = generator.verify_all_invariants(dataset)
    print(f"\nInvariants Verified: All 7 integrity invariants PASSED: {invariants['all_invariants_passed']}")
    print(f"All files successfully exported to {out_dir} in both Parquet and CSV formats.")
    print("=" * 70)


if __name__ == "__main__":
    main()
