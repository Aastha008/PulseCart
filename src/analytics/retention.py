"""
PulseCart Monthly Cohort Retention & Lifetime Value (LTV) Engine
Feature F17 / Milestone 3

Computes:
1. Monthly cohort retention matrices (Month 0 to Month 6+).
2. Verification of Month 0 = 100% and retention decay monotonicity.
3. Repeat purchase rates (count and % of purchasing users with >= 2 orders).
4. Customer Lifetime Value (LTV) curves partitioned by customer_segment and cohort month.
"""

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CohortRetentionRecord:
    cohort_month: str
    initial_cohort_size: int
    retention_rates: Dict[int, float]
    active_users: Dict[int, int]
    revenue_by_month: Dict[int, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RetentionAnalyzer:
    """Cohort retention, repeat purchasing, and customer lifetime value processor."""

    def __init__(
        self,
        retention_path: Optional[Union[str, Path]] = None,
        orders_path: Optional[Union[str, Path]] = None,
        retention_df: Optional[pd.DataFrame] = None,
        orders_df: Optional[pd.DataFrame] = None,
    ):
        self.retention_path = Path(retention_path) if retention_path else None
        self.orders_path = Path(orders_path) if orders_path else None
        self._retention_df = retention_df.copy() if retention_df is not None else None
        self._orders_df = orders_df.copy() if orders_df is not None else None

    def _resolve_file(
        self, custom_path: Optional[Path], filename_stem: str
    ) -> pd.DataFrame:
        """Helper to resolve parquet or csv data file."""
        if custom_path is not None:
            candidates = [custom_path]
            if custom_path.suffix == ".parquet":
                candidates.append(custom_path.with_suffix(".csv"))
            elif custom_path.suffix == ".csv":
                candidates.insert(0, custom_path.with_suffix(".parquet"))
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "marts"
            candidates = [
                base_dir / f"{filename_stem}.parquet",
                base_dir / f"{filename_stem}.csv",
            ]

        for p in candidates:
            if p.exists():
                try:
                    if p.suffix == ".parquet":
                        logger.info(f"Loading {filename_stem} from {p}")
                        return pd.read_parquet(p)
                    else:
                        logger.info(f"Loading {filename_stem} from CSV fallback {p}")
                        return pd.read_csv(p)
                except Exception as e:
                    logger.warning(f"Error reading {p}: {e}")

        raise FileNotFoundError(
            f"Could not load {filename_stem} from any candidate path: {[str(p) for p in candidates]}"
        )

    def load_retention_data(self) -> pd.DataFrame:
        """Loads fct_user_retention fact data."""
        if self._retention_df is None:
            self._retention_df = self._resolve_file(
                self.retention_path, "fct_user_retention"
            )
        return self._retention_df

    def load_orders_data(self) -> pd.DataFrame:
        """Loads fct_orders fact data."""
        if self._orders_df is None:
            self._orders_df = self._resolve_file(self.orders_path, "fct_orders")
        return self._orders_df

    @staticmethod
    def _standardize_month(val: Any) -> str:
        """Formats timestamp/string into YYYY-MM."""
        s = str(val)[:7]
        return s

    def calculate_cohort_retention_matrix(
        self, df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Builds the monthly cohort retention matrix (Month 0 to Month 6+).
        Returns a DataFrame where rows are cohort_months and columns are month offsets (0, 1, 2, ...).
        Values are retention percentages (0.0 to 100.0).
        """
        if df is None:
            df = self.load_retention_data()

        if len(df) == 0:
            return pd.DataFrame()

        df_work = df.copy()
        df_work["cohort_month_str"] = df_work["cohort_month"].apply(
            self._standardize_month
        )

        offset_col = (
            "month_offset" if "month_offset" in df_work.columns else "month_number"
        )
        df_work["month_offset_int"] = df_work[offset_col].astype(int)

        # Revenue column resolution
        rev_col = "revenue_in_month"
        if rev_col not in df_work.columns:
            rev_col = (
                "monthly_revenue" if "monthly_revenue" in df_work.columns else None
            )

        # Group by cohort and offset
        agg_dict: Dict[str, Any] = {"user_id": "nunique"}
        if rev_col:
            agg_dict[rev_col] = "sum"

        grouped = (
            df_work.groupby(["cohort_month_str", "month_offset_int"])
            .agg(agg_dict)
            .reset_index()
        )
        grouped.rename(columns={"user_id": "active_users"}, inplace=True)

        # Determine M0 cohort sizes
        m0_sizes = (
            grouped[grouped["month_offset_int"] == 0]
            .set_index("cohort_month_str")["active_users"]
            .to_dict()
        )

        # If any cohort is missing M0, calculate total unique users in that cohort as fallback
        all_cohorts = grouped["cohort_month_str"].unique()
        for c in all_cohorts:
            if c not in m0_sizes or m0_sizes[c] == 0:
                total_c_users = df_work[df_work["cohort_month_str"] == c][
                    "user_id"
                ].nunique()
                m0_sizes[c] = total_c_users

        grouped["initial_cohort_size"] = grouped["cohort_month_str"].map(m0_sizes)
        grouped["retention_rate"] = grouped.apply(
            lambda r: (
                round((r["active_users"] / r["initial_cohort_size"]) * 100.0, 2)
                if r["initial_cohort_size"] > 0
                else 0.0
            ),
            axis=1,
        )

        # Pivot into cohort retention matrix
        pivot_df = grouped.pivot(
            index="cohort_month_str",
            columns="month_offset_int",
            values="retention_rate",
        ).fillna(0.0)

        pivot_df.index.name = "cohort_month"
        return pivot_df

    def verify_retention_invariants(
        self, df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Verifies core mathematical invariants:
        1. Month 0 retention is exactly 100.0% for all cohorts.
        2. No subsequent month exceeds Month 0 active user count.
        3. Measures overall monotonic decay behavior.
        """
        if df is None:
            df = self.load_retention_data()

        if len(df) == 0:
            return {
                "month_0_is_100_percent": True,
                "decay_monotonic_vs_m0": True,
                "all_decay_monotonic": True,
                "cohort_count": 0,
                "violations": [],
            }

        matrix = self.calculate_cohort_retention_matrix(df)
        violations: List[str] = []

        # Check 1: Month 0 is 100%
        m0_is_100 = True
        if 0 in matrix.columns:
            for cohort, rate in matrix[0].items():
                if abs(rate - 100.0) > 0.01:
                    m0_is_100 = False
                    violations.append(
                        f"Cohort {cohort} Month 0 retention is {rate}%, expected 100.0%"
                    )
        else:
            m0_is_100 = False
            violations.append("Month offset 0 column is missing from retention matrix")

        # Check 2: Subsequent months do not exceed 100%
        decay_vs_m0 = True
        subsequent_cols = [col for col in matrix.columns if col > 0]
        for col in subsequent_cols:
            for cohort, rate in matrix[col].items():
                if rate > 100.0:
                    decay_vs_m0 = False
                    violations.append(
                        f"Cohort {cohort} Month {col} retention is {rate}% > 100%"
                    )

        # Check 3: Strict monotonicity check between successive months
        all_decay_monotonic = True
        sorted_cols = sorted(matrix.columns)
        for i in range(1, len(sorted_cols)):
            curr_col = sorted_cols[i]
            prev_col = sorted_cols[i - 1]
            for cohort in matrix.index:
                curr_val = matrix.loc[cohort, curr_col]
                prev_val = matrix.loc[cohort, prev_col]
                # If current month has data, should generally be <= prev month
                if curr_val > prev_val + 0.01:
                    all_decay_monotonic = False

        return {
            "month_0_is_100_percent": m0_is_100,
            "decay_monotonic_vs_m0": decay_vs_m0,
            "all_decay_monotonic": all_decay_monotonic,
            "cohort_count": len(matrix),
            "violations": violations,
        }

    def calculate_repeat_purchase_rate(
        self, orders_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Calculates repeat purchase rates:
        - Total purchasing users (>= 1 order)
        - Repeat purchasing users (>= 2 orders)
        - Repeat purchase rate % = (repeat / total) * 100
        Also slices by customer_segment, country, and acquisition_channel if present.
        """
        if orders_df is None:
            orders_df = self.load_orders_data()

        if len(orders_df) == 0:
            return {
                "total_purchasing_users": 0,
                "repeat_purchasing_users": 0,
                "repeat_purchase_rate": 0.0,
                "by_customer_segment": {},
                "by_country": {},
            }

        # Filter completed orders if status column is present
        if "status" in orders_df.columns:
            active_orders = orders_df[orders_df["status"] == "completed"]
            if len(active_orders) == 0:
                active_orders = orders_df
        else:
            active_orders = orders_df

        # Overall repeat purchase metrics
        user_order_counts = (
            active_orders.groupby("user_id")["order_id"].nunique().to_dict()
        )
        total_purchasers = len(user_order_counts)
        repeat_purchasers = sum(
            1 for cnt in user_order_counts.values() if cnt >= 2
        )

        rpr = (
            round((repeat_purchasers / total_purchasers) * 100.0, 2)
            if total_purchasers > 0
            else 0.0
        )

        # Segment breakdowns
        def compute_group_rpr(group_col: str) -> Dict[str, Dict[str, Any]]:
            if group_col not in active_orders.columns:
                return {}
            breakdown: Dict[str, Dict[str, Any]] = {}
            for g_val, g_df in active_orders.groupby(group_col):
                u_counts = g_df.groupby("user_id")["order_id"].nunique()
                t_users = len(u_counts)
                r_users = int((u_counts >= 2).sum())
                rate = (
                    round((r_users / t_users) * 100.0, 2) if t_users > 0 else 0.0
                )
                breakdown[str(g_val)] = {
                    "total_users": t_users,
                    "repeat_users": r_users,
                    "repeat_purchase_rate": rate,
                }
            return breakdown

        by_segment = compute_group_rpr("customer_segment")
        by_country = compute_group_rpr("country")

        return {
            "total_purchasing_users": int(total_purchasers),
            "repeat_purchasing_users": int(repeat_purchasers),
            "repeat_purchase_rate": float(rpr),
            "by_customer_segment": by_segment,
            "by_country": by_country,
        }

    def calculate_ltv_curves(
        self, df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Calculates customer lifetime value (LTV) curves partitioned by
        customer_segment and cohort_month across elapsed month_offsets.
        """
        if df is None:
            df = self.load_retention_data()

        if len(df) == 0:
            return pd.DataFrame()

        df_work = df.copy()
        df_work["cohort_month_str"] = df_work["cohort_month"].apply(
            self._standardize_month
        )

        offset_col = (
            "month_offset" if "month_offset" in df_work.columns else "month_number"
        )
        df_work["month_offset_int"] = df_work[offset_col].astype(int)

        rev_col = "revenue_in_month"
        if rev_col not in df_work.columns:
            rev_col = (
                "monthly_revenue" if "monthly_revenue" in df_work.columns else None
            )

        segment_col = (
            "customer_segment"
            if "customer_segment" in df_work.columns
            else "segment"
        )
        has_segment = segment_col in df_work.columns

        group_keys = (
            ["customer_segment", "cohort_month_str", "month_offset_int"]
            if has_segment
            else ["cohort_month_str", "month_offset_int"]
        )

        agg_dict: Dict[str, Any] = {"user_id": "nunique"}
        if rev_col:
            agg_dict[rev_col] = "sum"

        grouped = df_work.groupby(group_keys).agg(agg_dict).reset_index()
        grouped.rename(columns={"user_id": "active_users"}, inplace=True)
        if rev_col and rev_col != "revenue":
            grouped.rename(columns={rev_col: "revenue"}, inplace=True)
        elif not rev_col:
            grouped["revenue"] = 0.0
        grouped["revenue"] = pd.to_numeric(grouped["revenue"], errors="coerce").fillna(0.0).astype(float)

        # Sort order for cumulative accumulation
        sort_keys = (
            ["customer_segment", "cohort_month_str", "month_offset_int"]
            if has_segment
            else ["cohort_month_str", "month_offset_int"]
        )
        grouped.sort_values(by=sort_keys, inplace=True)

        partition_keys = (
            ["customer_segment", "cohort_month_str"]
            if has_segment
            else ["cohort_month_str"]
        )

        # Initial cohort size per partition
        m0_grouped = grouped[grouped["month_offset_int"] == 0].set_index(
            partition_keys
        )["active_users"]
        m0_map = m0_grouped.to_dict()

        def get_cohort_size(row: pd.Series) -> int:
            if has_segment:
                key = (row["customer_segment"], row["cohort_month_str"])
            else:
                key = row["cohort_month_str"]
            size = m0_map.get(key, 0)
            if size == 0:
                # Fallback: total unique users in segment cohort
                cond = df_work["cohort_month_str"] == row["cohort_month_str"]
                if has_segment:
                    cond = cond & (df_work["customer_segment"] == row["customer_segment"])
                size = df_work[cond]["user_id"].nunique()
            return max(1, size)

        grouped["cohort_initial_size"] = grouped.apply(get_cohort_size, axis=1)

        # Cumulative revenue and cumulative average LTV per user
        grouped["cumulative_revenue"] = (
            grouped.groupby(partition_keys)["revenue"].cumsum().round(2)
        )
        grouped["cumulative_ltv"] = (
            grouped["cumulative_revenue"] / grouped["cohort_initial_size"]
        ).round(2)

        return grouped

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Executes complete retention analysis suite and formats for JSON reporting.
        """
        retention_df = self.load_retention_data()
        orders_df = self.load_orders_data()

        matrix_df = self.calculate_cohort_retention_matrix(retention_df)
        invariants = self.verify_retention_invariants(retention_df)
        repeat_purchases = self.calculate_repeat_purchase_rate(orders_df)
        ltv_df = self.calculate_ltv_curves(retention_df)

        # Format matrix for JSON
        matrix_records = []
        for cohort_idx, row in matrix_df.iterrows():
            matrix_records.append(
                {
                    "cohort_month": str(cohort_idx),
                    "retention_rates": {
                        f"M{col}": float(val) for col, val in row.items()
                    },
                }
            )

        # Format LTV curves
        ltv_records = ltv_df.to_dict(orient="records") if len(ltv_df) > 0 else []

        return {
            "total_cohorts": len(matrix_df),
            "retention_invariants": invariants,
            "cohort_retention_matrix": matrix_records,
            "repeat_purchase_metrics": repeat_purchases,
            "customer_lifetime_value_curves": ltv_records,
        }


def compute_cohort_retention(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience helper to compute cohort retention matrix from DataFrame."""
    analyzer = RetentionAnalyzer(retention_df=df)
    return analyzer.calculate_cohort_retention_matrix(df)
