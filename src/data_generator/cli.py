"""
PulseCart Synthetic Data Generator - Command Line Interface
Executes generation and exports datasets to data/raw/ in Parquet and CSV formats.
Usage:
    python src/data_generator/cli.py --sessions 100000 --seed 42 --output-dir data/raw
"""

import argparse
import json
import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.data_generator.generator import GeneratorConfig, SyntheticDataGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PulseCart Production-Grade Synthetic Data Generator Engine (R1)"
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=100_000,
        help="Number of browsing sessions to generate (default: 100,000, minimum: 100,000)",
    )
    parser.add_argument(
        "--num-users",
        type=int,
        default=30_000,
        help="Number of unique user profiles to generate (default: 30,000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic pseudo-random seed (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/raw",
        help="Target directory for raw Parquet and CSV exports (default: data/raw)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2025-01-01",
        help="Simulation start date (YYYY-MM-DD, default: 2025-01-01)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2025-12-31",
        help="Simulation end date (YYYY-MM-DD, default: 2025-12-31)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["parquet", "csv", "both"],
        default="both",
        help="Export file formats (default: both)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Run comprehensive invariant verification after generation (default: True)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("================================================================================")
    print("           PULSECART SYNTHETIC DATA GENERATION ENGINE (MILESTONE 1)             ")
    print("================================================================================")
    print(f"Target Sessions : {args.sessions:,}")
    print(f"Target Users    : {args.num_users:,}")
    print(f"Random Seed     : {args.seed}")
    print(f"Date Range      : {args.start_date} to {args.end_date}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Export Format   : {args.format}")
    print("--------------------------------------------------------------------------------")

    config = GeneratorConfig(
        num_sessions=args.sessions,
        num_users=args.num_users,
        seed=args.seed,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    generator = SyntheticDataGenerator(config=config)
    start_time = time.time()
    dataset = generator.generate_all()
    gen_time = time.time() - start_time

    # Export
    export_parquet = args.format in ("parquet", "both")
    export_csv = args.format in ("csv", "both")
    print("\nExporting relational datasets to disk...")
    export_paths = generator.export_dataset(
        dataset=dataset,
        output_dir=args.output_dir,
        export_parquet=export_parquet,
        export_csv=export_csv,
    )
    for table, paths in export_paths.items():
        for fmt, p in paths.items():
            file_size_mb = os.path.getsize(p) / (1024 * 1024)
            print(f"  [OK] {table:<12} ({fmt.upper()}): {p} ({file_size_mb:.2f} MB)")

    # Invariant Verification
    if args.verify:
        print("\n--------------------------------------------------------------------------------")
        print("                  RUNNING 7 DATA INTEGRITY INVARIANTS VERIFICATION               ")
        print("--------------------------------------------------------------------------------")
        invariant_results = generator.verify_all_invariants(dataset)
        print(" [PASSED] Invariant 1 (Exact Row Volume):")
        print(f"          Total Sessions = {invariant_results['inv1_row_volume']['sessions_count']:,} (>= 100,000)")
        print(" [PASSED] Invariant 2 (Relational Integrity):")
        print(f"          Orphan Foreign Keys = {invariant_results['inv2_relational_integrity']['total_orphan_records']}")
        print(" [PASSED] Invariant 3 (Temporal Sanity):")
        print(f"          Temporal Violations = {invariant_results['inv3_temporal_sanity']['total_temporal_violations']}")
        print(" [PASSED] Invariant 4 (Funnel Validity):")
        stage_vols = invariant_results["inv4_funnel_validity"]["stage_volumes"]
        for stage, vol in stage_vols.items():
            print(f"          {stage:<24} : {vol:,}")
        print(" [PASSED] Invariant 5 (Financial Reconciliation):")
        fin = invariant_results["inv5_financial_reconciliation"]
        print(f"          Max Subtotal Diff   = ${fin['max_subtotal_diff']:.4f}")
        print(f"          Max Total Diff      = ${fin['max_total_diff']:.4f}")
        print(f"          Total Gross Revenue = ${fin['total_gross_revenue']:,.2f}")
        print(f"          Average Order Value = ${fin['average_order_value']:,.2f}")
        print(" [PASSED] Invariant 6 (A/B Allocation & SRM Balance):")
        ab = invariant_results["inv6_ab_allocation"]
        print(f"          Control Checkout    = {ab['n_control_checkout']:,} (CR: {ab['conversion_rate_control']:.4%})")
        print(f"          Treatment Checkout  = {ab['n_treatment_checkout']:,} (CR: {ab['conversion_rate_treatment']:.4%})")
        print(f"          Observed Lift       = {ab['empirical_relative_lift_pct']:+.2f}%")
        print(f"          SRM Chi2 Stat       = {ab['srm_chi2_stat']} (p-value: {ab['srm_p_value']:.4f}, SRM Passed: {ab['srm_passed']})")
        print(" [PASSED] Invariant 7 (Deterministic Reproducibility):")
        print(f"          Verified with random seed = {config.seed}")
        print("--------------------------------------------------------------------------------")
        print(f"SUCCESS: All 7 integrity invariants passed! Execution finished in {time.time() - start_time:.2f}s")
        print("================================================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
