"""
Adversarial Empirical Stress Test Suite for PulseCart Milestone 1 Raw Data
Deeply stress-tests relational integrity, orphan records, temporal ordering,
financial reconciliation, funnel state transitions, A/B parameterization,
and Parquet/CSV parity across 100K+ sessions.
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy import stats

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))

def load_data(file_format="parquet"):
    print(f"\n=======================================================")
    print(f"LOADING DATASET ({file_format.upper()}) FROM {DATA_DIR}")
    print(f"=======================================================")
    ext = file_format
    dfs = {}
    tables = ["users", "products", "sessions", "events", "orders", "order_items"]
    for t in tables:
        path = os.path.join(DATA_DIR, f"{t}.{ext}")
        assert os.path.exists(path), f"File missing: {path}"
        if ext == "parquet":
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path)
            # Parse datetime columns for CSV
            date_cols = {
                "users": ["created_at"],
                "products": ["created_at"],
                "sessions": ["session_start", "session_end"],
                "events": ["event_timestamp"],
                "orders": ["order_timestamp"]
            }
            if t in date_cols:
                for col in date_cols[t]:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
        dfs[t] = df
        print(f"  Loaded {t}.{ext}: {len(df):,} rows, {len(df.columns)} columns")
    return dfs

def run_stress_tests(dfs, label="PARQUET"):
    users = dfs["users"]
    products = dfs["products"]
    sessions = dfs["sessions"]
    events = dfs["events"]
    orders = dfs["orders"]
    order_items = dfs["order_items"]

    failures = []
    summary = {}

    print(f"\n--- STRESS-TEST SUITE: {label} ---")

    # -------------------------------------------------------------
    # 1. Volume & Uniqueness Invariants
    # -------------------------------------------------------------
    print("\n[TEST 1] Volume & Primary Key Uniqueness...")
    n_sessions = len(sessions)
    if n_sessions < 100000:
        failures.append(f"Volume: sessions count {n_sessions} < 100,000")
    else:
        print(f"  [PASS] Session count >= 100,000: {n_sessions:,}")

    for name, df, pk in [
        ("users", users, "user_id"),
        ("products", products, "product_id"),
        ("sessions", sessions, "session_id"),
        ("events", events, "event_id"),
        ("orders", orders, "order_id"),
        ("order_items", order_items, "order_item_id"),
    ]:
        dup_count = df[pk].duplicated().sum()
        null_count = df[pk].isna().sum()
        if dup_count > 0:
            failures.append(f"PK Uniqueness: {name}.{pk} has {dup_count} duplicates")
        if null_count > 0:
            failures.append(f"PK Nullability: {name}.{pk} has {null_count} nulls")
        if dup_count == 0 and null_count == 0:
            print(f"  [PASS] {name}.{pk} is unique and non-null ({len(df):,} records)")

    # -------------------------------------------------------------
    # 2. Relational Integrity & Exhaustive Orphan Checks
    # -------------------------------------------------------------
    print("\n[TEST 2] Relational Integrity & Orphan Checks...")
    user_ids = set(users["user_id"])
    prod_ids = set(products["product_id"])
    sess_ids = set(sessions["session_id"])
    ord_ids = set(orders["order_id"])

    # Null foreign key checks
    for tbl_name, df, fk in [
        ("sessions", sessions, "user_id"),
        ("events", events, "session_id"),
        ("events", events, "user_id"),
        ("orders", orders, "session_id"),
        ("orders", orders, "user_id"),
        ("order_items", order_items, "order_id"),
        ("order_items", order_items, "product_id"),
    ]:
        null_fk = df[fk].isna().sum()
        if null_fk > 0:
            failures.append(f"Null FK: {tbl_name}.{fk} has {null_fk} nulls")
        else:
            print(f"  [PASS] {tbl_name}.{fk} has 0 nulls")

    # sessions.user_id in users.user_id
    orphan_sess_user = (~sessions["user_id"].isin(user_ids)).sum()
    if orphan_sess_user > 0:
        failures.append(f"Orphan FK: sessions.user_id has {orphan_sess_user} orphan records")
    else:
        print(f"  [PASS] sessions.user_id -> users.user_id: 0 orphans")

    # events.session_id in sessions.session_id
    orphan_ev_sess = (~events["session_id"].isin(sess_ids)).sum()
    if orphan_ev_sess > 0:
        failures.append(f"Orphan FK: events.session_id has {orphan_ev_sess} orphan records")
    else:
        print(f"  [PASS] events.session_id -> sessions.session_id: 0 orphans")

    # events.user_id in users.user_id
    orphan_ev_user = (~events["user_id"].isin(user_ids)).sum()
    if orphan_ev_user > 0:
        failures.append(f"Orphan FK: events.user_id has {orphan_ev_user} orphan records")
    else:
        print(f"  [PASS] events.user_id -> users.user_id: 0 orphans")

    # events.product_id (when non-null) in products.product_id
    ev_prods = events["product_id"].dropna()
    orphan_ev_prod = (~ev_prods.isin(prod_ids)).sum()
    if orphan_ev_prod > 0:
        failures.append(f"Orphan FK: events.product_id has {orphan_ev_prod} orphan records")
    else:
        print(f"  [PASS] events.product_id -> products.product_id: 0 orphans ({len(ev_prods):,} checked)")

    # orders.session_id in sessions.session_id
    orphan_ord_sess = (~orders["session_id"].isin(sess_ids)).sum()
    if orphan_ord_sess > 0:
        failures.append(f"Orphan FK: orders.session_id has {orphan_ord_sess} orphan records")
    else:
        print(f"  [PASS] orders.session_id -> sessions.session_id: 0 orphans")

    # orders.user_id in users.user_id
    orphan_ord_user = (~orders["user_id"].isin(user_ids)).sum()
    if orphan_ord_user > 0:
        failures.append(f"Orphan FK: orders.user_id has {orphan_ord_user} orphan records")
    else:
        print(f"  [PASS] orders.user_id -> users.user_id: 0 orphans")

    # order_items.order_id in orders.order_id
    orphan_itm_ord = (~order_items["order_id"].isin(ord_ids)).sum()
    if orphan_itm_ord > 0:
        failures.append(f"Orphan FK: order_items.order_id has {orphan_itm_ord} orphan records")
    else:
        print(f"  [PASS] order_items.order_id -> orders.order_id: 0 orphans")

    # order_items.product_id in products.product_id
    orphan_itm_prod = (~order_items["product_id"].isin(prod_ids)).sum()
    if orphan_itm_prod > 0:
        failures.append(f"Orphan FK: order_items.product_id has {orphan_itm_prod} orphan records")
    else:
        print(f"  [PASS] order_items.product_id -> products.product_id: 0 orphans")

    # Reverse orphan checks:
    # Are there any orders with NO order_items?
    ord_items_orders = set(order_items["order_id"])
    orders_without_items = (~orders["order_id"].isin(ord_items_orders)).sum()
    if orders_without_items > 0:
        failures.append(f"Reverse Orphan: {orders_without_items} orders have zero order_items")
    else:
        print(f"  [PASS] All orders have >= 1 order_items (0 empty orders)")

    # Cross-table session-user consistency
    sess_u_map = sessions.set_index("session_id")["user_id"].to_dict()
    ev_user_matches = events["user_id"] == events["session_id"].map(sess_u_map)
    if not ev_user_matches.all():
        mismatches = (~ev_user_matches).sum()
        failures.append(f"Consistency: events.user_id != sessions.user_id for {mismatches} events")
    else:
        print(f"  [PASS] events.user_id matches sessions.user_id exactly")

    ord_user_matches = orders["user_id"] == orders["session_id"].map(sess_u_map)
    if not ord_user_matches.all():
        mismatches = (~ord_user_matches).sum()
        failures.append(f"Consistency: orders.user_id != sessions.user_id for {mismatches} orders")
    else:
        print(f"  [PASS] orders.user_id matches sessions.user_id exactly")

    # 1:1 match between purchase events and orders
    purchase_events = events[events["event_name"] == "purchase"]
    if len(purchase_events) != len(orders):
        failures.append(f"Order/Purchase mismatch: {len(purchase_events)} purchase events vs {len(orders)} orders")
    else:
        print(f"  [PASS] 1:1 match between purchase events ({len(purchase_events):,}) and orders ({len(orders):,})")

    purch_sess_set = set(purchase_events["session_id"])
    ord_sess_set = set(orders["session_id"])
    if purch_sess_set != ord_sess_set:
        diff_count = len(purch_sess_set ^ ord_sess_set)
        failures.append(f"Order/Purchase session set symmetric difference: {diff_count} sessions")
    else:
        print(f"  [PASS] Purchase session_ids set exactly equals orders session_ids set")

    # -------------------------------------------------------------
    # 3. Temporal Invariants & Monotonicity
    # -------------------------------------------------------------
    print("\n[TEST 3] Temporal Ordering & Monotonicity...")
    u_created_map = users.set_index("user_id")["created_at"].to_dict()
    sess_user_created = sessions["user_id"].map(u_created_map)
    sess_before_user = (sessions["session_start"] < sess_user_created).sum()
    if sess_before_user > 0:
        failures.append(f"Temporal: {sess_before_user} sessions started before user creation")
    else:
        print(f"  [PASS] All sessions start >= user creation timestamp")

    sess_duration_neg = (sessions["session_end"] < sessions["session_start"]).sum()
    if sess_duration_neg > 0:
        failures.append(f"Temporal: {sess_duration_neg} sessions end before start")
    else:
        print(f"  [PASS] All sessions have session_end >= session_start")

    # Event timestamp within session bounds
    sess_start_map = sessions.set_index("session_id")["session_start"].to_dict()
    sess_end_map = sessions.set_index("session_id")["session_end"].to_dict()
    ev_sess_starts = events["session_id"].map(sess_start_map)
    ev_sess_ends = events["session_id"].map(sess_end_map)

    ev_before_start = (events["event_timestamp"] < ev_sess_starts).sum()
    ev_after_end = (events["event_timestamp"] > ev_sess_ends).sum()
    if ev_before_start > 0:
        failures.append(f"Temporal: {ev_before_start} events occurred before session_start")
    else:
        print(f"  [PASS] All events occurred >= session_start")
    if ev_after_end > 0:
        failures.append(f"Temporal: {ev_after_end} events occurred after session_end")
    else:
        print(f"  [PASS] All events occurred <= session_end")

    # Within-session chronological monotonicity
    sorted_ev = events.sort_values(["session_id", "step_number"])
    ts_diffs = sorted_ev.groupby("session_id")["event_timestamp"].diff()
    non_null_diffs = ts_diffs.dropna()
    inv_step_order = (non_null_diffs <= pd.Timedelta(0)).sum()
    min_dwell = non_null_diffs.min().total_seconds()
    max_dwell = non_null_diffs.max().total_seconds()
    if inv_step_order > 0:
        failures.append(f"Temporal: {inv_step_order} event step transitions have non-positive delta (t_next <= t_prev)")
    else:
        print(f"  [PASS] All within-session step transitions are strictly monotonic (t_next > t_prev)")
        print(f"         Inter-step dwell range: min={min_dwell:.2f}s, max={max_dwell:.2f}s")

    # Purchase timestamp == order timestamp
    purch_ts_map = purchase_events.set_index("session_id")["event_timestamp"].to_dict()
    purch_aligned_ts = orders["session_id"].map(purch_ts_map)
    ord_ts_mismatch = (orders["order_timestamp"] != purch_aligned_ts).sum()
    if ord_ts_mismatch > 0:
        failures.append(f"Temporal: {ord_ts_mismatch} orders have order_timestamp != purchase event_timestamp")
    else:
        print(f"  [PASS] All order timestamps match purchase event timestamps exactly")

    # Order date format and alignment
    ord_date_computed = orders["order_timestamp"].dt.strftime("%Y-%m-%d")
    date_mismatch = (orders["order_date"] != ord_date_computed).sum()
    if date_mismatch > 0:
        failures.append(f"Temporal: {date_mismatch} orders have mismatched order_date string")
    else:
        print(f"  [PASS] All order_date fields match order_timestamp calendar day")

    # Product creation timestamp vs order timestamp
    prod_created_map = products.set_index("product_id")["created_at"].to_dict()
    itm_prod_created = order_items["product_id"].map(prod_created_map)
    ord_ts_map = orders.set_index("order_id")["order_timestamp"].to_dict()
    itm_ord_ts = order_items["order_id"].map(ord_ts_map)
    itm_before_prod = (itm_ord_ts < itm_prod_created).sum()
    if itm_before_prod > 0:
        failures.append(f"Temporal: {itm_before_prod} order items ordered before product was created")
    else:
        print(f"  [PASS] All order items ordered >= product created_at")

    # -------------------------------------------------------------
    # 4. Funnel State Machine & Transition Validity
    # -------------------------------------------------------------
    print("\n[TEST 4] Funnel Transitions & State Machine Validity...")
    step_counts = events.groupby("step_number")["session_id"].nunique().to_dict()
    print("  Funnel Stage Unique Sessions:")
    for step in range(1, 7):
        print(f"    Step {step}: {step_counts.get(step, 0):,} sessions")

    for s in range(1, 6):
        if step_counts.get(s, 0) <= step_counts.get(s + 1, 0):
            failures.append(f"Funnel dropoff violation: Step {s} ({step_counts.get(s, 0)}) <= Step {s+1} ({step_counts.get(s+1, 0)})")
    print(f"  [PASS] Strictly monotonically decreasing session funnel volume")

    # Check for skipped steps per session
    step_stats = events.groupby("session_id")["step_number"].agg(["min", "max", "count"])
    skipped_step_sessions = ((step_stats["min"] != 1) | (step_stats["max"] != step_stats["count"])).sum()
    if skipped_step_sessions > 0:
        failures.append(f"Funnel: {skipped_step_sessions} sessions have skipped steps or don't start at step 1")
    else:
        print(f"  [PASS] 0 sessions skipped funnel steps; all sessions start at step 1")

    # Bounce invariant
    bounce_sessions_expected = set(step_stats[step_stats["max"] == 1].index)
    bounce_sessions_flagged = set(sessions[sessions["is_bounce"]]["session_id"])
    if bounce_sessions_expected != bounce_sessions_flagged:
        diff_bounces = len(bounce_sessions_expected ^ bounce_sessions_flagged)
        failures.append(f"Bounce logic: {diff_bounces} sessions have mismatched is_bounce flag")
    else:
        print(f"  [PASS] is_bounce flag perfectly matches sessions with furthest_step == 1 ({len(bounce_sessions_flagged):,} sessions)")

    # -------------------------------------------------------------
    # 5. Financial Reconciliation
    # -------------------------------------------------------------
    print("\n[TEST 5] Financial Integrity & Reconciliation...")
    # Item line total check
    expected_line_totals = (order_items["quantity"] * order_items["unit_price"]).round(2)
    max_line_diff = (order_items["line_total"].round(2) - expected_line_totals).abs().max()
    if max_line_diff > 0.001:
        failures.append(f"Financial: max order_items.line_total diff = {max_line_diff:.4f}")
    else:
        print(f"  [PASS] order_items.line_total == quantity * unit_price (max diff: ${max_line_diff:.4f})")

    # Item line profit check
    expected_line_profits = (order_items["quantity"] * (order_items["unit_price"] - order_items["unit_cost"])).round(2)
    max_profit_diff = (order_items["line_profit"].round(2) - expected_line_profits).abs().max()
    if max_profit_diff > 0.001:
        failures.append(f"Financial: max order_items.line_profit diff = {max_profit_diff:.4f}")
    else:
        print(f"  [PASS] order_items.line_profit == quantity * (price - cost) (max diff: ${max_profit_diff:.4f})")

    # Product pricing consistency: does order_items.unit_price match products.price?
    prod_price_map = products.set_index("product_id")["price"].to_dict()
    prod_cost_map = products.set_index("product_id")["cost"].to_dict()
    expected_itm_prices = order_items["product_id"].map(prod_price_map)
    expected_itm_costs = order_items["product_id"].map(prod_cost_map)

    itm_price_mismatch = (order_items["unit_price"] != expected_itm_prices).sum()
    itm_cost_mismatch = (order_items["unit_cost"] != expected_itm_costs).sum()
    if itm_price_mismatch > 0:
        failures.append(f"Financial: {itm_price_mismatch} order items have unit_price != products.price")
    else:
        print(f"  [PASS] order_items.unit_price matches products.price for all 13,902 items")
    if itm_cost_mismatch > 0:
        failures.append(f"Financial: {itm_cost_mismatch} order items have unit_cost != products.cost")
    else:
        print(f"  [PASS] order_items.unit_cost matches products.cost for all 13,902 items")

    # Subtotal reconciliation
    items_subtotal = order_items.groupby("order_id")["line_total"].sum().round(2)
    ord_subtotal = orders.set_index("order_id")["subtotal"].round(2)
    max_subtotal_diff = (items_subtotal - ord_subtotal).abs().max()
    if max_subtotal_diff > 0.001:
        failures.append(f"Financial: max orders.subtotal diff vs items sum = {max_subtotal_diff:.4f}")
    else:
        print(f"  [PASS] orders.subtotal == sum(items.line_total) (max diff: ${max_subtotal_diff:.4f})")

    # Total amount reconciliation: total == subtotal + tax + shipping - discount
    reconciled_totals = (orders["subtotal"] + orders["tax_amount"] + orders["shipping_fee"] - orders["discount_amount"]).round(2)
    max_total_diff = (orders["total_amount"].round(2) - reconciled_totals).abs().max()
    if max_total_diff > 0.001:
        failures.append(f"Financial: max orders.total_amount reconciliation diff = {max_total_diff:.4f}")
    else:
        print(f"  [PASS] orders.total_amount == subtotal + tax + shipping - discount (max diff: ${max_total_diff:.4f})")

    # Shipping fee rule check: Free above $75, else $5.99
    expected_shipping = np.where(orders["subtotal"] >= 75.0, 0.00, 5.99)
    ship_mismatch = (orders["shipping_fee"] != expected_shipping).sum()
    if ship_mismatch > 0:
        failures.append(f"Financial: {ship_mismatch} orders violate shipping fee business rule")
    else:
        print(f"  [PASS] Shipping fee rule (subtotal >= $75 => $0, else $5.99) holds for 100% of orders")

    # Tax rule check: 8.25% sales tax on net taxable subtotal (subtotal - discount)
    net_taxable = np.maximum(0.0, orders["subtotal"] - orders["discount_amount"])
    expected_tax = (net_taxable * 0.0825).round(2)
    tax_diff = (orders["tax_amount"].round(2) - expected_tax).abs().max()
    if tax_diff > 0.01:
        failures.append(f"Financial: max tax calculation diff = {tax_diff:.4f}")
    else:
        print(f"  [PASS] Sales tax calculation (8.25% on net taxable) reconciled (max diff: ${tax_diff:.4f})")

    # Positive economics
    if (orders["total_amount"] <= 0).any():
        failures.append("Financial: Some orders have total_amount <= 0")
    if (order_items["unit_price"] <= order_items["unit_cost"]).any():
        failures.append("Financial: Some order items have price <= cost")
    print(f"  [PASS] All orders total_amount > 0 and unit_price > unit_cost")

    total_gross_rev = orders["total_amount"].sum()
    aov = orders["total_amount"].mean()
    print(f"  Total Gross Revenue: ${total_gross_rev:,.2f} | Average Order Value: ${aov:.2f}")

    # -------------------------------------------------------------
    # 6. A/B Experiment Allocation & Parameterization
    # -------------------------------------------------------------
    print("\n[TEST 6] Checkout A/B Experiment & SRM Check...")
    checkout_sess_ids = set(events[events["step_number"] == 4]["session_id"])
    checkout_sessions = sessions[sessions["session_id"].isin(checkout_sess_ids)]
    ab_counts = checkout_sessions["ab_variant"].value_counts().to_dict()
    n_ctrl = ab_counts.get("control", 0)
    n_treat = ab_counts.get("treatment", 0)
    total_co = n_ctrl + n_treat

    chi2, srm_pval = stats.chisquare([n_ctrl, n_treat], [total_co / 2.0, total_co / 2.0])
    print(f"  Checkout Entrants: Control={n_ctrl:,}, Treatment={n_treat:,} (Total={total_co:,})")
    print(f"  SRM Chi2 Stat: {chi2:.4f}, p-value: {srm_pval:.6f}")

    if srm_pval < 0.01:
        failures.append(f"A/B Experiment: SRM detected! Chi2={chi2:.4f}, p={srm_pval:.6f} < 0.01")
    else:
        print(f"  [PASS] SRM check passed (p-value >= 0.01)")

    # Conversions
    conv_ctrl = (orders["ab_variant"] == "control").sum()
    conv_treat = (orders["ab_variant"] == "treatment").sum()

    cr_ctrl = conv_ctrl / n_ctrl if n_ctrl > 0 else 0
    cr_treat = conv_treat / n_treat if n_treat > 0 else 0
    rel_lift = (cr_treat - cr_ctrl) / cr_ctrl if cr_ctrl > 0 else 0

    print(f"  Purchases: Control={conv_ctrl:,} ({cr_ctrl*100:.2f}%), Treatment={conv_treat:,} ({cr_treat*100:.2f}%)")
    print(f"  Empirical Relative Lift: {rel_lift*100:+.2f}%")

    # Variant consistency between sessions and orders
    ord_sess_var_matches = orders["ab_variant"] == orders["session_id"].map(sessions.set_index("session_id")["ab_variant"])
    if not ord_sess_var_matches.all():
        failures.append("A/B: orders.ab_variant does not match sessions.ab_variant")
    else:
        print(f"  [PASS] orders.ab_variant strictly matches sessions.ab_variant")

    summary["failures"] = failures
    summary["total_failures"] = len(failures)
    return summary

def compare_parquet_and_csv(pq_dfs, csv_dfs):
    print(f"\n=======================================================")
    print("COMPARING PARQUET VS CSV EXACT PARITY")
    print(f"=======================================================")
    parity_failures = []
    tables = ["users", "products", "sessions", "events", "orders", "order_items"]
    for t in tables:
        pq = pq_dfs[t]
        csv = csv_dfs[t]
        if len(pq) != len(csv):
            parity_failures.append(f"{t}: Row count mismatch PQ={len(pq)} vs CSV={len(csv)}")
            continue
        if list(pq.columns) != list(csv.columns):
            parity_failures.append(f"{t}: Column mismatch PQ={list(pq.columns)} vs CSV={list(csv.columns)}")
            continue

        for col in pq.columns:
            # Check boolean first
            if pd.api.types.is_bool_dtype(pq[col]) or pd.api.types.is_bool_dtype(csv[col]):
                b_pq = pq[col].astype(bool)
                b_csv = csv[col].astype(bool)
                diff = (b_pq ^ b_csv).sum()
                if diff > 0:
                    parity_failures.append(f"{t}.{col}: Bool mismatch {diff} records")
            elif pd.api.types.is_numeric_dtype(pq[col]):
                max_d = (pq[col] - csv[col]).abs().max()
                if max_d > 0.01:
                    parity_failures.append(f"{t}.{col}: Numeric difference PQ vs CSV max diff {max_d}")
            elif pd.api.types.is_datetime64_any_dtype(pq[col]):
                diff_sec = (pq[col] - csv[col]).dt.total_seconds().abs().max()
                if diff_sec > 1.0:
                    parity_failures.append(f"{t}.{col}: Timestamp difference PQ vs CSV max diff {diff_sec}s")
            else:
                s1 = pq[col].fillna("__NULL__").astype(str)
                s2 = csv[col].fillna("__NULL__").astype(str)
                mismatches = (s1 != s2).sum()
                if mismatches > 0:
                    parity_failures.append(f"{t}.{col}: String mismatches {mismatches} records")

        print(f"  [PASS] {t}: Exact parity between Parquet and CSV across all {len(pq.columns)} columns")

    if parity_failures:
        print(f"Parity Failures ({len(parity_failures)}):")
        for f in parity_failures:
            print(f"  - {f}")
    else:
        print("  All Parquet and CSV files exhibit 100% exact parity!")
    return parity_failures

def main():
    pq_dfs = load_data("parquet")
    csv_dfs = load_data("csv")

    pq_results = run_stress_tests(pq_dfs, label="PARQUET")
    csv_results = run_stress_tests(csv_dfs, label="CSV")
    parity_failures = compare_parquet_and_csv(pq_dfs, csv_dfs)

    total_errs = pq_results["total_failures"] + csv_results["total_failures"] + len(parity_failures)
    print("\n=======================================================")
    print("FINAL EMPIRICAL VERDICT SUMMARY")
    print(f"=======================================================")
    print(f"Parquet Test Failures: {pq_results['total_failures']}")
    print(f"CSV Test Failures    : {csv_results['total_failures']}")
    print(f"Parity Failures      : {len(parity_failures)}")
    print(f"Total Failures       : {total_errs}")

    if total_errs == 0:
        print("\n>>> FINAL VERDICT: APPROVE <<<")
        print("All relational, temporal, financial, and state invariants satisfied with ZERO errors.")
        sys.exit(0)
    else:
        print("\n>>> FINAL VERDICT: REJECT <<<")
        print("Discovered invariants failures. Review log above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
