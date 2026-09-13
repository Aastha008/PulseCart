"""
PulseCart E2E Test Suite - Root Fixtures and Test Harness
Provides fixtures, synthetic dataset generators, DuckDB in-memory database,
and mathematical reference oracles for all 4 testing tiers.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytest
from scipy import stats

# Ensure pulsecart root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Pytest Markers Configuration
# ---------------------------------------------------------------------------
def pytest_configure(config):
    """Register custom markers for the 4-tier testing hierarchy."""
    config.addinivalue_line("markers", "tier1: Tier 1 - Feature Coverage tests")
    config.addinivalue_line("markers", "tier2: Tier 2 - Boundary & Corner Case tests")
    config.addinivalue_line("markers", "tier3: Tier 3 - Cross-Feature Combination tests")
    config.addinivalue_line("markers", "tier4: Tier 4 - Real-World Application Scenario tests")
    config.addinivalue_line("markers", "feature(name): Feature ID under test (e.g. F01, F06)")


# ---------------------------------------------------------------------------
# Path & Directory Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns absolute Path to project root."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def raw_data_dir(project_root: Path) -> Path:
    """Returns path to raw data directory."""
    return project_root / "data" / "raw"


@pytest.fixture(scope="session")
def dbt_dir(project_root: Path) -> Path:
    """Returns path to dbt project directory."""
    return project_root / "dbt_pulsecart"


@pytest.fixture(scope="session")
def reports_dir(project_root: Path) -> Path:
    """Returns path to analytics reports directory."""
    return project_root / "reports"


@pytest.fixture(scope="session")
def docs_dir(project_root: Path) -> Path:
    """Returns path to documentation directory."""
    return project_root / "docs"


@pytest.fixture(scope="session")
def power_bi_dir(project_root: Path) -> Path:
    """Returns path to Power BI specifications and assets."""
    return project_root / "power_bi"


# ---------------------------------------------------------------------------
# Random Number Generator Fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def rng() -> np.random.Generator:
    """Deterministic seeded random number generator."""
    return np.random.default_rng(seed=42)


# ---------------------------------------------------------------------------
# Synthetic Reference Dataset Generator & Fixture
# ---------------------------------------------------------------------------
def generate_reference_products(num_products: int = 100, seed: int = 42) -> pd.DataFrame:
    """Generates standard conformed product catalog."""
    rng = np.random.default_rng(seed=seed)
    categories = ["Electronics", "Apparel", "Home & Kitchen", "Beauty", "Sports"]
    adjectives = ["Wireless", "Ultra", "Classic", "Premium", "Eco-Friendly", "Smart", "Compact"]
    nouns = ["Headphones", "T-Shirt", "Coffee Maker", "Face Cream", "Yoga Mat", "Smartwatch", "Backpack"]

    records = []
    for i in range(num_products):
        pid = f"PRD-{i+1:05d}"
        cat = categories[i % len(categories)]
        adj = adjectives[rng.integers(0, len(adjectives))]
        noun = nouns[rng.integers(0, len(nouns))]
        name = f"{adj} {noun} {i+1}"
        
        # Base pricing by category
        base_cost = float(rng.uniform(10.0, 120.0))
        markup = float(rng.uniform(1.3, 2.5))
        price = round(base_cost * markup, 2)
        cost = round(base_cost, 2)
        margin = round(price - cost, 2)
        inv = int(rng.integers(50, 1000))
        created = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        records.append({
            "product_id": pid,
            "product_name": name,
            "category": cat,
            "cost": cost,
            "price": price,
            "margin": margin,
            "inventory_count": inv,
            "created_at": created,
        })
    return pd.DataFrame(records)


def generate_reference_users(num_users: int = 250, seed: int = 42) -> pd.DataFrame:
    """Generates conformed users dataset."""
    rng = np.random.default_rng(seed=seed)
    countries = ["US", "UK", "CA", "DE", "FR", "AU"]
    country_weights = [0.45, 0.18, 0.12, 0.10, 0.08, 0.07]
    channels = ["Organic Search", "Paid Search", "Direct", "Social", "Email", "Referral"]
    channel_weights = [0.28, 0.24, 0.18, 0.15, 0.10, 0.05]
    segments = ["VIP", "Regular", "Bargain"]
    segment_weights = [0.15, 0.60, 0.25]
    devices = ["Mobile", "Desktop", "Tablet"]
    device_weights = [0.55, 0.35, 0.10]

    records = []
    base_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(num_users):
        uid = f"USR-{i+1:08d}"
        days_offset = rng.integers(0, 120)
        secs_offset = rng.integers(0, 86400)
        created_at = base_date + timedelta(days=int(days_offset), seconds=int(secs_offset))
        
        country = rng.choice(countries, p=country_weights)
        channel = rng.choice(channels, p=channel_weights)
        segment = rng.choice(segments, p=segment_weights)
        device = rng.choice(devices, p=device_weights)

        records.append({
            "user_id": uid,
            "created_at": created_at,
            "country": country,
            "acquisition_channel": channel,
            "customer_segment": segment,
            "device_preference": device,
        })
    return pd.DataFrame(records)


def generate_reference_bundle(
    num_users: int = 300,
    num_sessions: int = 1200,
    seed: int = 42,
    treatment_lift: float = 0.089
) -> Dict[str, pd.DataFrame]:
    """
    Generates a fully compliant, relational, deterministic reference bundle
    satisfying all 7 invariants and schemas.
    """
    rng = np.random.default_rng(seed=seed)
    df_products = generate_reference_products(num_products=50, seed=seed)
    df_users = generate_reference_users(num_users=num_users, seed=seed)
    user_map = df_users.set_index("user_id").to_dict("index")
    product_records = df_products.to_dict("records")

    sessions_records = []
    events_records = []
    orders_records = []
    order_items_records = []

    stages = [
        (1, "landing_page", 0.62),
        (2, "product_view", 0.44),
        (3, "add_to_cart", 0.48),
        (4, "checkout_started", 0.72),
        (5, "payment_started", 0.80),
        (6, "purchase", 1.00),
    ]

    event_counter = 0
    order_counter = 0
    item_counter = 0

    user_ids = df_users["user_id"].tolist()

    for s_idx in range(num_sessions):
        sid = f"SES-{s_idx+1:09d}"
        uid = rng.choice(user_ids)
        u_info = user_map[uid]

        u_created = u_info["created_at"]
        s_offset_days = rng.integers(0, 30)
        s_offset_secs = rng.integers(60, 86400)
        session_start = u_created + timedelta(days=int(s_offset_days), seconds=int(s_offset_secs))

        # Device, country, traffic source
        device = rng.choice(["Mobile", "Desktop", "Tablet"], p=[0.55, 0.35, 0.10])
        country = u_info["country"]
        traffic_source = u_info["acquisition_channel"]
        is_returning = bool(rng.random() < 0.35)
        ab_variant = "treatment" if (s_idx % 2 == 1) else "control"

        # Funnel state machine traversal
        current_time = session_start
        reached_stages = []
        is_bounce = True
        cart_value = 0.0
        selected_prod = rng.choice(product_records)

        # Stage 1: landing
        reached_stages.append((1, "landing_page"))
        event_counter += 1
        current_time += timedelta(seconds=float(rng.lognormal(mean=2.5, sigma=0.5)))
        events_records.append({
            "event_id": f"EVT-{event_counter:010d}",
            "session_id": sid,
            "user_id": uid,
            "event_timestamp": current_time,
            "event_name": "landing_page",
            "event_type": "landing_page",
            "step_number": 1,
            "page_url": "/",
            "product_id": None,
            "cart_value": 0.0,
        })

        # Progression check for stages 2 to 6
        for step, name, base_p in stages[1:]:
            p = base_p
            # Variant modulation on checkout/payment
            if name == "payment_started" and ab_variant == "treatment":
                p = min(0.98, p * 1.045)
            elif name == "purchase" and ab_variant == "treatment":
                p = min(0.98, p * 1.0421)

            if rng.random() <= p:
                is_bounce = False
                reached_stages.append((step, name))
                event_counter += 1
                current_time += timedelta(seconds=float(rng.lognormal(mean=2.8, sigma=0.6)))
                
                prod_id = selected_prod["product_id"] if step in (2, 3) else None
                if step == 3:
                    cart_value = selected_prod["price"]

                events_records.append({
                    "event_id": f"EVT-{event_counter:010d}",
                    "session_id": sid,
                    "user_id": uid,
                    "event_timestamp": current_time,
                    "event_name": name,
                    "event_type": name,
                    "step_number": step,
                    "page_url": f"/step/{name}",
                    "product_id": prod_id,
                    "cart_value": cart_value,
                })
            else:
                break

        session_end = current_time + timedelta(seconds=float(rng.uniform(5.0, 30.0)))
        sessions_records.append({
            "session_id": sid,
            "user_id": uid,
            "session_start": session_start,
            "session_end": session_end,
            "device_type": device,
            "country": country,
            "traffic_source": traffic_source,
            "channel": traffic_source,
            "is_bounce": is_bounce,
            "is_returning_user": is_returning,
            "is_new_user": not is_returning,
            "ab_variant": ab_variant,
            "experiment_id": "exp_checkout_streamline_v1",
        })

        # Check if reached purchase
        if reached_stages[-1][0] == 6:
            order_counter += 1
            oid = f"ORD-{order_counter:08d}"
            purchase_ts = current_time
            qty = int(rng.integers(1, 3))
            unit_p = selected_prod["price"]
            unit_c = selected_prod["cost"]
            subtotal = round(unit_p * qty, 2)
            tax = round(subtotal * 0.08, 2)
            shipping = 0.0 if subtotal > 100.0 else 9.99
            discount = 10.0 if (u_info["customer_segment"] == "VIP" and subtotal > 50) else 0.0
            total = round(subtotal + tax + shipping - discount, 2)
            pay_method = rng.choice(["Credit Card", "Apple Pay", "PayPal", "Klarna"])

            orders_records.append({
                "order_id": oid,
                "session_id": sid,
                "user_id": uid,
                "order_date": purchase_ts.strftime("%Y-%m-%d"),
                "order_timestamp": purchase_ts,
                "subtotal": subtotal,
                "tax_amount": tax,
                "shipping_fee": shipping,
                "discount_amount": discount,
                "total_amount": total,
                "payment_method": pay_method,
                "status": "completed",
                "ab_variant": ab_variant,
            })

            item_counter += 1
            line_total = round(unit_p * qty, 2)
            line_cost = round(unit_c * qty, 2)
            line_profit = round(line_total - line_cost, 2)
            order_items_records.append({
                "order_item_id": f"ITM-{item_counter:09d}",
                "order_id": oid,
                "product_id": selected_prod["product_id"],
                "quantity": qty,
                "unit_price": unit_p,
                "unit_cost": unit_c,
                "line_total": line_total,
                "total_item_price": line_total,
                "line_profit": line_profit,
            })

    return {
        "users": df_users,
        "products": df_products,
        "sessions": pd.DataFrame(sessions_records),
        "events": pd.DataFrame(events_records),
        "orders": pd.DataFrame(orders_records),
        "order_items": pd.DataFrame(order_items_records),
    }


@pytest.fixture(scope="session")
def ref_data_bundle() -> Dict[str, pd.DataFrame]:
    """Session-scoped synthetic data bundle with guaranteed relational integrity."""
    return generate_reference_bundle(num_users=300, num_sessions=1500, seed=42)


# ---------------------------------------------------------------------------
# DuckDB In-Memory SQL Fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def duckdb_conn(ref_data_bundle: Dict[str, pd.DataFrame]):
    """Provides an in-memory DuckDB connection with all reference tables loaded."""
    import duckdb
    conn = duckdb.connect(database=":memory:")
    for table_name, df in ref_data_bundle.items():
        conn.register(f"raw_{table_name}", df)
        conn.register(table_name, df)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Mathematical Verification Oracles
# ---------------------------------------------------------------------------
def oracle_compute_srm_chi2(n_ctrl: int, n_treat: int, p: float = 0.5) -> Tuple[float, float, bool]:
    """
    Authoritative calculation of Pearson Chi-Square Goodness-of-Fit for SRM.
    Returns: (chi2_statistic, p_value, srm_passed)
    """
    total = n_ctrl + n_treat
    if total == 0:
        return 0.0, 1.0, True
    e_ctrl = total * p
    e_treat = total * (1.0 - p)
    chi2 = ((n_ctrl - e_ctrl) ** 2) / e_ctrl + ((n_treat - e_treat) ** 2) / e_treat
    p_val = float(1.0 - stats.chi2.cdf(chi2, df=1))
    srm_passed = bool(p_val >= 0.01)
    return float(chi2), p_val, srm_passed


def oracle_compute_two_proportion_ztest(
    n_ctrl: int,
    conv_ctrl: int,
    n_treat: int,
    conv_treat: int,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Authoritative two-proportion z-test with pooled SE and Delta method 95% CI.
    """
    p_c = conv_ctrl / n_ctrl if n_ctrl > 0 else 0.0
    p_t = conv_treat / n_treat if n_treat > 0 else 0.0
    abs_diff = p_t - p_c
    rel_lift = (p_t - p_c) / p_c if p_c > 0 else 0.0

    p_pool = (conv_ctrl + conv_treat) / (n_ctrl + n_treat) if (n_ctrl + n_treat) > 0 else 0.0
    se_pool = np.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_ctrl + 1.0 / n_treat)) if (n_ctrl > 0 and n_treat > 0) else 0.0
    z_score = abs_diff / se_pool if se_pool > 0 else 0.0
    p_value = float(2.0 * (1.0 - stats.norm.cdf(abs(z_score))))

    se_unpooled = np.sqrt((p_c * (1.0 - p_c) / n_ctrl) + (p_t * (1.0 - p_t) / n_treat)) if (n_ctrl > 0 and n_treat > 0) else 0.0
    z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
    ci_abs_lower = abs_diff - z_crit * se_unpooled
    ci_abs_upper = abs_diff + z_crit * se_unpooled
    ci_rel_lower = ci_abs_lower / p_c if p_c > 0 else 0.0
    ci_rel_upper = ci_abs_upper / p_c if p_c > 0 else 0.0

    return {
        "conversion_rate_control": p_c,
        "conversion_rate_treatment": p_t,
        "absolute_difference": abs_diff,
        "relative_lift": rel_lift,
        "pooled_se": se_pool,
        "z_score": z_score,
        "p_value": p_value,
        "ci_abs_lower": ci_abs_lower,
        "ci_abs_upper": ci_abs_upper,
        "ci_rel_lower": ci_rel_lower,
        "ci_rel_upper": ci_rel_upper,
        "statistically_significant": bool(p_value < alpha),
    }


def oracle_compute_funnel_metrics(events_df: pd.DataFrame, sessions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Authoritative computation of multi-stage funnel volume, conversion %, and drop-off %.
    """
    stages = [
        "landing_page",
        "product_view",
        "add_to_cart",
        "checkout_started",
        "payment_started",
        "purchase",
    ]
    total_sessions = len(sessions_df)
    results = []
    prev_count = total_sessions

    for step_num, stage in enumerate(stages, 1):
        sessions_reached = events_df[events_df["event_type"] == stage]["session_id"].nunique()
        step_conv = (sessions_reached / prev_count * 100.0) if prev_count > 0 else 0.0
        overall_conv = (sessions_reached / total_sessions * 100.0) if total_sessions > 0 else 0.0
        abs_drop = prev_count - sessions_reached if step_num > 1 else total_sessions - sessions_reached
        drop_pct = (abs_drop / prev_count * 100.0) if prev_count > 0 else 0.0

        results.append({
            "step_number": step_num,
            "stage_name": stage,
            "sessions_count": sessions_reached,
            "step_conversion_rate": round(step_conv, 2),
            "overall_conversion_rate": round(overall_conv, 2),
            "absolute_drop_off": abs_drop,
            "drop_off_rate": round(drop_pct, 2),
        })
        prev_count = sessions_reached

    return pd.DataFrame(results)


def oracle_verify_financial_integrity(orders_df: pd.DataFrame, order_items_df: pd.DataFrame) -> bool:
    """
    Verifies subtotal matching line items sum and total matching equation.
    """
    if len(orders_df) == 0:
        return True
    item_sums = order_items_df.groupby("order_id")["total_item_price"].sum().to_dict()
    for _, row in orders_df.iterrows():
        oid = row["order_id"]
        expected_subtotal = item_sums.get(oid, 0.0)
        if abs(row["subtotal"] - expected_subtotal) > 0.01:
            return False
        expected_total = row["subtotal"] + row["tax_amount"] + row["shipping_fee"] - row["discount_amount"]
        if abs(row["total_amount"] - expected_total) > 0.01:
            return False
    return True


def oracle_verify_timestamp_monotonicity(
    sessions_df: pd.DataFrame,
    events_df: pd.DataFrame,
    orders_df: pd.DataFrame
) -> bool:
    """
    Verifies session_start <= min(event_ts) <= max(event_ts) <= session_end.
    """
    if len(events_df) == 0:
        return True
    
    events_agg = events_df.groupby("session_id")["event_timestamp"].agg(["min", "max"]).to_dict("index")
    sess_map = sessions_df.set_index("session_id").to_dict("index")

    for sid, bounds in events_agg.items():
        if sid not in sess_map:
            return False
        s_row = sess_map[sid]
        s_start = pd.to_datetime(s_row["session_start"])
        s_end = pd.to_datetime(s_row["session_end"])
        e_min = pd.to_datetime(bounds["min"])
        e_max = pd.to_datetime(bounds["max"])

        if s_start > e_min or e_max > s_end:
            return False
    return True
