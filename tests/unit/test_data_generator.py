"""
PulseCart Synthetic Data Generator - Unit Test Suite
Validates schema compliance, relational integrity, temporal monotonicity,
financial reconciliation, A/B parameterization, and seed determinism.
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.data_generator.generator import GeneratorConfig, SyntheticDataGenerator
from src.data_generator.distributions import (
    PRODUCT_CATEGORIES_CONFIG,
    STAGE_NAMES,
    COUNTRY_DISTRIBUTION,
    CHANNEL_DISTRIBUTION,
    SEGMENT_DISTRIBUTION,
)


@pytest.fixture(scope="module")
def small_generator():
    """Provides a generator configured for fast test execution."""
    config = GeneratorConfig(
        num_sessions=3_000,
        num_users=1_000,
        seed=42,
        start_date="2025-01-01",
        end_date="2025-06-30",
    )
    return SyntheticDataGenerator(config=config)


@pytest.fixture(scope="module")
def small_dataset(small_generator):
    """Generates a small synthetic dataset for testing."""
    return small_generator.generate_all()


class TestProductCatalog:
    """Tests for synthetic product catalog generation."""

    def test_product_catalog_size_and_categories(self, small_generator):
        products_df = small_generator.generate_products()
        assert len(products_df) == 100, f"Expected 100 products, got {len(products_df)}"
        assert products_df["category"].nunique() == 5
        counts_per_category = products_df["category"].value_counts()
        for cat in PRODUCT_CATEGORIES_CONFIG.keys():
            assert counts_per_category[cat] == 20, f"Category {cat} should have 20 items"

    def test_product_economic_sanity(self, small_generator):
        products_df = small_generator.generate_products()
        # Price and cost must be strictly positive
        assert (products_df["price"] > 0).all()
        assert (products_df["cost"] > 0).all()
        # Price must exceed cost strictly
        assert (products_df["price"] > products_df["cost"]).all()
        # Margin must equal price - cost (within 0.01)
        expected_margin = (products_df["price"] - products_df["cost"]).round(2)
        diff = (products_df["margin"].round(2) - expected_margin).abs().max()
        assert diff < 0.01, f"Product margin mismatch: max diff {diff}"

    def test_product_id_format(self, small_generator):
        products_df = small_generator.generate_products()
        assert products_df["product_id"].is_unique
        assert products_df["product_id"].str.match(r"^PRD-\d{5}$").all()


class TestUserGeneration:
    """Tests for user master profile generation."""

    def test_user_volume_and_uniqueness(self, small_generator):
        users_df = small_generator.generate_users()
        assert len(users_df) == small_generator.config.num_users
        assert users_df["user_id"].is_unique
        assert users_df["user_id"].str.match(r"^USR-\d{8}$").all()

    def test_user_demographic_domains(self, small_generator):
        users_df = small_generator.generate_users()
        assert set(users_df["country"].unique()).issubset(set(COUNTRY_DISTRIBUTION.keys()))
        assert set(users_df["acquisition_channel"].unique()).issubset(set(CHANNEL_DISTRIBUTION.keys()))
        assert set(users_df["customer_segment"].unique()).issubset(set(SEGMENT_DISTRIBUTION.keys()))
        assert set(users_df["device_preference"].unique()).issubset({"Desktop", "Mobile", "Tablet"})

    def test_user_created_at_bounds(self, small_generator):
        users_df = small_generator.generate_users()
        start_ts = pd.Timestamp(small_generator.config.start_date)
        end_ts = pd.Timestamp(small_generator.config.end_date)
        assert (users_df["created_at"] >= start_ts).all()
        assert (users_df["created_at"] <= end_ts).all()


class TestSessionGeneration:
    """Tests for browsing session generation."""

    def test_session_volume_and_fk_integrity(self, small_generator):
        users_df = small_generator.generate_users()
        sessions_df = small_generator.generate_sessions(users_df)
        assert len(sessions_df) == small_generator.config.num_sessions
        assert sessions_df["session_id"].is_unique
        assert sessions_df["session_id"].str.match(r"^SES-\d{9}$").all()
        # Referential integrity to users
        assert sessions_df["user_id"].isin(set(users_df["user_id"])).all()

    def test_session_start_after_user_creation(self, small_generator):
        users_df = small_generator.generate_users()
        sessions_df = small_generator.generate_sessions(users_df)
        u_map = users_df.set_index("user_id")["created_at"].to_dict()
        user_created = sessions_df["user_id"].map(u_map)
        assert (sessions_df["session_start"] >= user_created).all()

    def test_ab_variant_split_balance(self, small_generator):
        users_df = small_generator.generate_users()
        sessions_df = small_generator.generate_sessions(users_df)
        variant_counts = sessions_df["ab_variant"].value_counts()
        assert "control" in variant_counts and "treatment" in variant_counts
        # 50/50 allocation sanity check
        total = len(sessions_df)
        ctrl_ratio = variant_counts["control"] / total
        assert 0.46 < ctrl_ratio < 0.54, f"Control ratio {ctrl_ratio:.4f} outside balanced window"


class TestFunnelAndClickstream:
    """Tests for funnel stage progression and telemetry events."""

    def test_stage_sequence_strictly_monotonic_dropoff(self, small_dataset):
        events = small_dataset.events
        stage_counts = events.groupby("step_number")["session_id"].nunique().to_dict()
        # Verify landing > product_view > add_to_cart > checkout_started > payment_started > purchase
        steps = [1, 2, 3, 4, 5, 6]
        counts = [stage_counts.get(s, 0) for s in steps]
        for i in range(len(counts) - 1):
            assert counts[i] > counts[i + 1], f"Step {steps[i]} count ({counts[i]}) not > Step {steps[i+1]} count ({counts[i+1]})"

    def test_no_skipped_funnel_stages(self, small_dataset):
        events = small_dataset.events
        sess_max_step = events.groupby("session_id")["step_number"].max()
        sess_step_count = events.groupby("session_id")["step_number"].count()
        # If no stages are skipped, step_number count must equal max step number
        assert (sess_max_step == sess_step_count).all()

    def test_temporal_monotonicity_in_sessions(self, small_dataset):
        events = small_dataset.events
        sessions = small_dataset.sessions
        # Check event_timestamps strictly ascending per session
        sorted_ev = events.sort_values(["session_id", "step_number"])
        time_diffs = sorted_ev.groupby("session_id")["event_timestamp"].diff().dropna()
        assert (time_diffs > pd.Timedelta(0)).all()

        # Check session_start <= min(event) and max(event) <= session_end
        min_ev = events.groupby("session_id")["event_timestamp"].min()
        max_ev = events.groupby("session_id")["event_timestamp"].max()
        s_map_start = sessions.set_index("session_id")["session_start"].to_dict()
        s_map_end = sessions.set_index("session_id")["session_end"].to_dict()

        for sid in min_ev.index[:200]:  # spot check sample
            assert s_map_start[sid] <= min_ev[sid]
            assert max_ev[sid] <= s_map_end[sid]


class TestOrdersAndFinancialIntegrity:
    """Tests for order creation, line items, and financial reconciliation."""

    def test_orders_match_purchase_events_one_to_one(self, small_dataset):
        events = small_dataset.events
        orders = small_dataset.orders
        purchases = events[events["event_name"] == "purchase"]
        assert len(orders) == len(purchases)
        assert set(orders["session_id"]) == set(purchases["session_id"])

    def test_order_timestamp_matches_purchase_event_timestamp(self, small_dataset):
        events = small_dataset.events
        orders = small_dataset.orders
        purchases = events[events["event_name"] == "purchase"].set_index("session_id")["event_timestamp"]
        orders_ts = orders.set_index("session_id")["order_timestamp"]
        aligned = purchases.loc[orders_ts.index]
        assert (aligned == orders_ts).all()

    def test_financial_reconciliation(self, small_dataset):
        orders = small_dataset.orders
        order_items = small_dataset.order_items

        # 1. Line items sum to order subtotal
        items_subtotal = order_items.groupby("order_id")["line_total"].sum().round(2)
        orders_subtotal = orders.set_index("order_id")["subtotal"].round(2)
        diff = (items_subtotal - orders_subtotal).abs().max()
        assert diff < 0.01, f"Subtotal mismatch: max diff {diff}"

        # 2. Total amount reconciles: subtotal + tax + shipping - discount
        expected_total = (orders["subtotal"] + orders["tax_amount"] + orders["shipping_fee"] - orders["discount_amount"]).round(2)
        total_diff = (orders["total_amount"].round(2) - expected_total).abs().max()
        assert total_diff < 0.01, f"Total amount mismatch: max diff {total_diff}"

        # 3. All orders have positive total amount
        assert (orders["total_amount"] > 0).all()

        # 4. Line item calculation: quantity * unit_price == line_total
        expected_line = (order_items["quantity"] * order_items["unit_price"]).round(2)
        line_diff = (order_items["line_total"].round(2) - expected_line).abs().max()
        assert line_diff < 0.01, f"Line item total mismatch: max diff {line_diff}"


class TestExperimentAndInvariants:
    """Tests for A/B experiment parameters, SRM checks, and determinism."""

    def test_srm_goodness_of_fit(self, small_dataset):
        from scipy import stats
        sessions = small_dataset.sessions
        events = small_dataset.events

        checkout_sess = events[events["event_name"] == "checkout_started"]["session_id"]
        ab_counts = sessions[sessions["session_id"].isin(checkout_sess)]["ab_variant"].value_counts()
        n_c = ab_counts.get("control", 0)
        n_t = ab_counts.get("treatment", 0)
        total = n_c + n_t

        _, p_val = stats.chisquare(f_obs=[n_c, n_t], f_exp=[total / 2.0, total / 2.0])
        assert p_val >= 0.01, f"SRM detected in test: p-value {p_val:.6f} < 0.01"

    def test_seed_determinism(self):
        """Verify identical seed produces bitwise-identical dataset."""
        cfg = GeneratorConfig(num_sessions=1_000, num_users=400, seed=999)
        gen1 = SyntheticDataGenerator(config=cfg)
        ds1 = gen1.generate_all()

        gen2 = SyntheticDataGenerator(config=cfg)
        ds2 = gen2.generate_all()

        pd.testing.assert_frame_equal(ds1.users, ds2.users)
        pd.testing.assert_frame_equal(ds1.products, ds2.products)
        pd.testing.assert_frame_equal(ds1.sessions, ds2.sessions)
        pd.testing.assert_frame_equal(ds1.events, ds2.events)
        pd.testing.assert_frame_equal(ds1.orders, ds2.orders)
        pd.testing.assert_frame_equal(ds1.order_items, ds2.order_items)

    def test_different_seeds_produce_different_data(self):
        """Verify different seeds produce divergent stochastic datasets."""
        cfg1 = GeneratorConfig(num_sessions=1_000, num_users=400, seed=101)
        cfg2 = GeneratorConfig(num_sessions=1_000, num_users=400, seed=202)
        ds1 = SyntheticDataGenerator(config=cfg1).generate_all()
        ds2 = SyntheticDataGenerator(config=cfg2).generate_all()

        assert not ds1.sessions["session_start"].equals(ds2.sessions["session_start"])
        assert not ds1.orders["total_amount"].equals(ds2.orders["total_amount"])


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
