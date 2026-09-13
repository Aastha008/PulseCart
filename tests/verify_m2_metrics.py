"""
PulseCart Milestone 2 Challenger Verification Script: Metric Consistency & Mathematical Correctness
Author: Challenger M2.2 (teamwork_preview_challenger)

Empirically stress-tests:
1. Financial Reconciliation across raw, staging, fct_orders, and dim_users.
2. Line total vs subtotal reconciliation.
3. Gross margin reconciliation.
4. Funnel monotonicity (session-level and population-level).
5. Cohort retention consistency in fct_user_retention (Month 0 = 100%, subsequent <= Month 0).
"""

import os
import sys
import json
from pathlib import Path
import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_dbt import DbtExecutionEngine

def run_checks():
    print("=" * 80)
    print("PULSECART M2 CHALLENGER EMPIRICAL VERIFICATION")
    print("=" * 80)

    # 1. Initialize dbt engine and materialize models in memory
    print("\n[STEP 1] Materializing all 18 dbt models in DuckDB...")
    engine = DbtExecutionEngine(db_path=":memory:")
    engine.ingest_raw_sources()
    engine.execute_models()
    conn = engine.conn

    report = {
        "financial_reconciliation": {},
        "line_total_subtotal": {},
        "gross_profit_reconciliation": {},
        "funnel_monotonicity": {},
        "cohort_retention": {},
        "verdict": "PENDING",
        "violations": []
    }

    # =========================================================================
    # 1. Financial Reconciliation
    # =========================================================================
    print("\n" + "=" * 80)
    print("CHECK 1: FINANCIAL RECONCILIATION ACROSS LAYERS")
    print("=" * 80)

    # A. Sum of total_amount across raw_orders, stg_orders, fct_orders, dim_users
    sum_raw = conn.execute("SELECT ROUND(SUM(total_amount), 2) FROM raw_orders").fetchone()[0]
    sum_stg = conn.execute("SELECT ROUND(SUM(total_amount), 2) FROM stg_orders").fetchone()[0]
    sum_fct = conn.execute("SELECT ROUND(SUM(total_amount), 2) FROM fct_orders").fetchone()[0]
    sum_dim = conn.execute("SELECT ROUND(SUM(lifetime_revenue), 2) FROM dim_users").fetchone()[0]

    report["financial_reconciliation"] = {
        "raw_orders_sum": float(sum_raw),
        "stg_orders_sum": float(sum_stg),
        "fct_orders_sum": float(sum_fct),
        "dim_users_sum": float(sum_dim),
        "diff_raw_stg": float(abs(sum_raw - sum_stg)),
        "diff_raw_fct": float(abs(sum_raw - sum_fct)),
        "diff_raw_dim": float(abs(sum_raw - sum_dim)),
    }

    print(f"  raw_orders total_amount:   ${sum_raw:,.2f}")
    print(f"  stg_orders total_amount:   ${sum_stg:,.2f}")
    print(f"  fct_orders total_amount:   ${sum_fct:,.2f}")
    print(f"  dim_users lifetime_revenue: ${sum_dim:,.2f}")

    if abs(sum_raw - sum_stg) > 0.001 or abs(sum_raw - sum_fct) > 0.001 or abs(sum_raw - sum_dim) > 0.001:
        msg = f"Financial discrepancy detected across layers! raw={sum_raw}, stg={sum_stg}, fct={sum_fct}, dim={sum_dim}"
        print(f"  [FAIL] {msg}")
        report["violations"].append(msg)
    else:
        print("  [PASS] Exact $0.00 difference across raw, stg, fct, and dim_users!")

    # B. Sum of line_total in order_items == Sum of subtotal in orders
    sum_line_total = conn.execute("SELECT ROUND(SUM(line_total), 2) FROM raw_order_items").fetchone()[0]
    sum_subtotal = conn.execute("SELECT ROUND(SUM(subtotal), 2) FROM raw_orders").fetchone()[0]
    diff_line_sub = round(abs(sum_line_total - sum_subtotal), 4)

    report["line_total_subtotal"] = {
        "order_items_line_total": float(sum_line_total),
        "orders_subtotal": float(sum_subtotal),
        "diff": float(diff_line_sub)
    }

    print(f"\n  order_items sum(line_total): ${sum_line_total:,.2f}")
    print(f"  orders sum(subtotal):        ${sum_subtotal:,.2f}")
    print(f"  Difference:                  ${diff_line_sub:,.4f}")

    if diff_line_sub > 0.001:
        msg = f"order_items.line_total vs orders.subtotal diff is ${diff_line_sub} > $0.00"
        print(f"  [FAIL] {msg}")
        report["violations"].append(msg)
    else:
        print("  [PASS] Exact $0.00 difference between order_items.line_total and orders.subtotal!")

    # C. Gross profit reconciliation
    # In fct_orders: gross_profit vs (subtotal - total_cogs) and vs total_amount accounting for tax/shipping/discount
    profit_check = conn.execute("""
        SELECT
            COUNT(*) AS total_orders,
            COUNT(CASE WHEN ROUND(gross_profit, 2) != ROUND(subtotal_amount - total_cogs, 2) THEN 1 END) AS subtotal_mismatches,
            COUNT(CASE WHEN ROUND(gross_profit, 2) != ROUND(total_amount - tax_amount - shipping_amount + discount_amount - total_cogs, 2) THEN 1 END) AS total_amount_mismatches,
            MAX(ABS(ROUND(gross_profit, 2) - ROUND(subtotal_amount - total_cogs, 2))) AS max_diff
        FROM fct_orders
    """).fetchone()

    total_orders, sub_mismatches, tot_mismatches, max_diff = profit_check
    report["gross_profit_reconciliation"] = {
        "total_orders": total_orders,
        "subtotal_mismatches": sub_mismatches,
        "total_amount_mismatches": tot_mismatches,
        "max_diff": float(max_diff or 0.0)
    }

    print(f"\n  Gross profit check across {total_orders:,} orders:")
    print(f"  gross_profit == subtotal - total_cost mismatches: {sub_mismatches}")
    print(f"  gross_profit == total_amount - tax - shipping + discount - total_cost mismatches: {tot_mismatches}")
    print(f"  Max difference: ${max_diff or 0.0:.4f}")

    if sub_mismatches > 0 or tot_mismatches > 0:
        msg = f"Gross profit reconciliation failed: {sub_mismatches} subtotal mismatches, {tot_mismatches} total_amount mismatches"
        print(f"  [FAIL] {msg}")
        report["violations"].append(msg)
    else:
        print("  [PASS] Gross profit reconciles perfectly across 100% of orders!")

    # =========================================================================
    # 2. Funnel Monotonicity
    # =========================================================================
    print("\n" + "=" * 80)
    print("CHECK 2: FUNNEL MONOTONICITY")
    print("=" * 80)

    # A. Per-session monotonicity:
    # reached_landing_page >= reached_product_view >= reached_add_to_cart >= reached_checkout_started >= reached_payment_started >= reached_purchase
    session_mono_check = conn.execute("""
        SELECT COUNT(*) 
        FROM fct_funnel
        WHERE NOT (
            reached_landing_page >= reached_product_view
            AND reached_product_view >= reached_add_to_cart
            AND reached_add_to_cart >= reached_checkout_started
            AND reached_checkout_started >= reached_payment_started
            AND reached_payment_started >= reached_purchase
        )
    """).fetchone()[0]

    # B. Population-level strictly decreasing step sums
    pop_steps = conn.execute("""
        SELECT
            SUM(reached_landing_page) AS step1_landing,
            SUM(reached_product_view) AS step2_product,
            SUM(reached_add_to_cart) AS step3_cart,
            SUM(reached_checkout_started) AS step4_checkout,
            SUM(reached_payment_started) AS step5_payment,
            SUM(reached_purchase) AS step6_purchase
        FROM fct_funnel
    """).fetchone()

    s1, s2, s3, s4, s5, s6 = pop_steps
    is_pop_monotonic = (s1 >= s2 >= s3 >= s4 >= s5 >= s6)

    report["funnel_monotonicity"] = {
        "session_monotonicity_violations": session_mono_check,
        "population_counts": {
            "landing_page": s1,
            "product_view": s2,
            "add_to_cart": s3,
            "checkout_started": s4,
            "payment_started": s5,
            "purchase": s6
        },
        "population_is_monotonic": is_pop_monotonic
    }

    print(f"  Session monotonicity violations (out of {conn.execute('SELECT COUNT(*) FROM fct_funnel').fetchone()[0]:,}): {session_mono_check}")
    print(f"  Population counts:")
    print(f"    1. Landing Page:      {s1:,}")
    print(f"    2. Product View:       {s2:,}")
    print(f"    3. Add to Cart:        {s3:,}")
    print(f"    4. Checkout Started:   {s4:,}")
    print(f"    5. Payment Started:    {s5:,}")
    print(f"    6. Purchase:           {s6:,}")

    if session_mono_check > 0:
        msg = f"Funnel session monotonicity violated in {session_mono_check} sessions!"
        print(f"  [FAIL] {msg}")
        report["violations"].append(msg)
    else:
        print("  [PASS] 100% of sessions strictly obey stage monotonicity!")

    if not is_pop_monotonic:
        msg = f"Funnel population step counts are not decreasing: {s1} -> {s2} -> {s3} -> {s4} -> {s5} -> {s6}"
        print(f"  [FAIL] {msg}")
        report["violations"].append(msg)
    else:
        print("  [PASS] Population step counts strictly decrease across all stages!")

    # =========================================================================
    # 3. Cohort Retention Consistency
    # =========================================================================
    print("\n" + "=" * 80)
    print("CHECK 3: COHORT RETENTION CONSISTENCY IN fct_user_retention")
    print("=" * 80)

    # Let's inspect what fct_user_retention actually contains
    cohort_sample = conn.execute("""
        SELECT cohort_month, month_offset, COUNT(DISTINCT user_id) as active_users, SUM(monthly_revenue) as revenue
        FROM fct_user_retention
        GROUP BY cohort_month, month_offset
        ORDER BY cohort_month, month_offset
    """).fetchall()

    print(f"  fct_user_retention cohort matrix rows: {len(cohort_sample)}")
    df_cohort = pd.DataFrame(cohort_sample, columns=["cohort_month", "month_offset", "active_users", "revenue"])
    print(df_cohort.head(15).to_string(index=False))

    # Check A: Month 0 users per cohort
    # Check if every cohort present in fct_user_retention has a month_offset = 0 row
    all_cohorts = df_cohort["cohort_month"].unique()
    m0_users = {}
    subsequent_exceeds = []

    for c in all_cohorts:
        sub_df = df_cohort[df_cohort["cohort_month"] == c]
        m0_row = sub_df[sub_df["month_offset"] == 0]
        if len(m0_row) == 0:
            m0_count = 0
            print(f"  [WARNING] Cohort {c} has NO month_offset = 0 row!")
        else:
            m0_count = int(m0_row["active_users"].iloc[0])
        m0_users[str(c)] = m0_count

        # Check if subsequent months exceed month 0 users
        subsequent = sub_df[sub_df["month_offset"] > 0]
        for _, row in subsequent.iterrows():
            offset = int(row["month_offset"])
            users = int(row["active_users"])
            if users > m0_count:
                subsequent_exceeds.append({
                    "cohort": str(c),
                    "month_offset": offset,
                    "m0_users": m0_count,
                    "offset_users": users
                })

    report["cohort_retention"] = {
        "total_cohorts": len(all_cohorts),
        "m0_users": m0_users,
        "subsequent_exceeds_m0_count": len(subsequent_exceeds),
        "subsequent_exceeds_details": subsequent_exceeds
    }

    print(f"\n  Cohorts analyzed: {len(all_cohorts)}")
    print(f"  Cases where active users in Month N > Month 0: {len(subsequent_exceeds)}")

    # Check if there is an issue with cohort_month definition (signup_cohort vs first_order_cohort)
    print("\n  Deep Dive on Cohort Definition:")
    user_first_order_compare = conn.execute("""
        WITH user_first_order AS (
            SELECT user_id, DATE_TRUNC('month', MIN(order_timestamp)) AS first_order_month
            FROM raw_orders
            GROUP BY user_id
        )
        SELECT
            COUNT(*) AS total_ordering_users,
            COUNT(CASE WHEN u.cohort_month != ufo.first_order_month THEN 1 END) AS signup_vs_first_order_diff
        FROM user_first_order ufo
        JOIN stg_users u ON ufo.user_id = u.user_id
    """).fetchone()

    total_ord_users, diff_cohort_users = user_first_order_compare
    print(f"    Total ordering users: {total_ord_users:,}")
    print(f"    Users where signup_month != first_order_month: {diff_cohort_users:,}")

    if len(subsequent_exceeds) > 0:
        print("\n  Detailed subsequent month exceeds:")
        for exc in subsequent_exceeds[:5]:
            print(f"    Cohort {exc['cohort']}: Month {exc['month_offset']} has {exc['offset_users']} users > Month 0 ({exc['m0_users']} users)")

    # Overall Verdict
    if len(report["violations"]) == 0 and len(subsequent_exceeds) == 0:
        report["verdict"] = "APPROVE"
    else:
        report["verdict"] = "REJECT"

    print("\n" + "=" * 80)
    print(f"OVERALL VERDICT: {report['verdict']}")
    print("=" * 80)

    # Save report to json for auditability
    out_path = PROJECT_ROOT / "reports" / "m2_challenger_verification_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to: {out_path}")

    return report


if __name__ == "__main__":
    run_checks()
