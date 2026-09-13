"""
PulseCart Multi-Stage Funnel Analytics Engine
Feature F16 / Milestone 3

Evaluates session volume, stage conversion rates, absolute drop-offs,
and percentage drop-off rates across the 6 e-commerce funnel stages:
1. landing_page
2. product_view
3. add_to_cart
4. checkout_started
5. payment_started
6. purchase

Supports dimensional slicing across:
- device_type
- traffic_source
- country
- customer_segment
"""

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

FUNNEL_STAGES: List[str] = [
    "landing_page",
    "product_view",
    "add_to_cart",
    "checkout_started",
    "payment_started",
    "purchase",
]

STAGE_FLAG_COLS: Dict[str, List[str]] = {
    "landing_page": ["reached_landing_page", "has_landing_page"],
    "product_view": ["reached_product_view", "has_product_view"],
    "add_to_cart": ["reached_add_to_cart", "has_add_to_cart"],
    "checkout_started": ["reached_checkout_started", "has_checkout_started"],
    "payment_started": ["reached_payment_started", "has_payment_started"],
    "purchase": ["reached_purchase", "has_purchase"],
}

SLICE_DIMENSIONS: List[str] = [
    "device_type",
    "traffic_source",
    "country",
    "customer_segment",
]


@dataclass
class FunnelStageMetric:
    step_number: int
    stage_name: str
    sessions_count: int
    step_conversion_rate: float
    overall_conversion_rate: float
    absolute_drop_off: int
    drop_off_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FunnelAnalyzer:
    """Multi-stage funnel analytics processor."""

    def __init__(
        self,
        data_path: Optional[Union[str, Path]] = None,
        df: Optional[pd.DataFrame] = None,
    ):
        self.data_path = Path(data_path) if data_path else None
        self._df = df.copy() if df is not None else None

    def load_data(self) -> pd.DataFrame:
        """Loads funnel fact data with Parquet preference and CSV fallback."""
        if self._df is not None:
            return self._df

        if self.data_path is not None:
            candidate_paths = [self.data_path]
            if self.data_path.suffix == ".parquet":
                candidate_paths.append(self.data_path.with_suffix(".csv"))
            elif self.data_path.suffix == ".csv":
                candidate_paths.insert(0, self.data_path.with_suffix(".parquet"))
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "marts"
            candidate_paths = [
                base_dir / "fct_funnel.parquet",
                base_dir / "fct_funnel.csv",
            ]

        for p in candidate_paths:
            if p.exists():
                try:
                    if p.suffix == ".parquet":
                        logger.info(f"Loading funnel data from {p}")
                        self._df = pd.read_parquet(p)
                    else:
                        logger.info(f"Loading funnel data from CSV fallback {p}")
                        self._df = pd.read_csv(p)
                    return self._df
                except Exception as e:
                    logger.warning(f"Failed to read {p}: {e}")

        raise FileNotFoundError(
            f"Could not load funnel dataset from any candidate path: {[str(p) for p in candidate_paths]}"
        )

    @staticmethod
    def _extract_stage_counts(df: pd.DataFrame) -> Dict[str, int]:
        """Extracts session counts reaching each stage from fact or raw events."""
        counts: Dict[str, int] = {}
        total_sessions = len(df)

        if total_sessions == 0:
            return {stage: 0 for stage in FUNNEL_STAGES}

        # Case 1: Raw events format (event_type or event_name column present)
        event_col = None
        if "event_type" in df.columns:
            event_col = "event_type"
        elif "event_name" in df.columns:
            event_col = "event_name"

        if event_col and "session_id" in df.columns:
            for stage in FUNNEL_STAGES:
                stage_sids = df[df[event_col] == stage]["session_id"].nunique()
                counts[stage] = int(stage_sids)
            return counts

        # Case 2: Fact table with milestone indicator flags (reached_* or has_*)
        for stage in FUNNEL_STAGES:
            matched_col = None
            for candidate in STAGE_FLAG_COLS[stage]:
                if candidate in df.columns:
                    matched_col = candidate
                    break

            if matched_col:
                # Can be boolean True/False or integer 1/0
                col_data = df[matched_col]
                if col_data.dtype == bool:
                    c = int(col_data.sum())
                else:
                    c = int((col_data.fillna(0).astype(int) > 0).sum())
                counts[stage] = c
            elif "furthest_step_reached" in df.columns:
                step_idx = FUNNEL_STAGES.index(stage) + 1
                c = int((df["furthest_step_reached"] >= step_idx).sum())
                counts[stage] = c
            else:
                counts[stage] = 0

        return counts

    # Public alias for stage counts extraction
    extract_stage_counts = _extract_stage_counts

    def evaluate_funnel(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Calculates funnel volume, conversion %, and drop-off % across 6 stages.
        Guarded against division by zero on empty slices.
        """
        if df is None:
            df = self.load_data()

        total_sessions = len(df)
        stage_counts = self._extract_stage_counts(df)

        results: List[Dict[str, Any]] = []
        prev_count = total_sessions

        for step_num, stage in enumerate(FUNNEL_STAGES, 1):
            sessions_reached = stage_counts.get(stage, 0)

            # Step conversion rate: % of preceding step (or total sessions for step 1)
            if prev_count > 0:
                step_conv = (sessions_reached / prev_count) * 100.0
            else:
                step_conv = 0.0

            # Overall conversion rate: % of initial session cohort
            if total_sessions > 0:
                overall_conv = (sessions_reached / total_sessions) * 100.0
            else:
                overall_conv = 0.0

            # Absolute drop-off: sessions lost between previous step and current step
            if step_num == 1:
                abs_drop = max(0, total_sessions - sessions_reached)
            else:
                abs_drop = max(0, prev_count - sessions_reached)

            # Drop-off rate %
            if prev_count > 0:
                drop_pct = (abs_drop / prev_count) * 100.0
            elif total_sessions > 0 and step_num == 1:
                drop_pct = (abs_drop / total_sessions) * 100.0
            else:
                drop_pct = 0.0

            metric = FunnelStageMetric(
                step_number=step_num,
                stage_name=stage,
                sessions_count=sessions_reached,
                step_conversion_rate=round(step_conv, 2),
                overall_conversion_rate=round(overall_conv, 2),
                absolute_drop_off=int(abs_drop),
                drop_off_rate=round(drop_pct, 2),
            )
            results.append(metric.to_dict())
            prev_count = sessions_reached

        return pd.DataFrame(results)

    def slice_by_dimension(
        self, dimension: str, df: Optional[pd.DataFrame] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Evaluates funnel metrics sliced across distinct categories of a dimension.
        """
        if df is None:
            df = self.load_data()

        if dimension not in df.columns:
            logger.warning(f"Dimension '{dimension}' not present in dataset.")
            return {}

        sliced_results: Dict[str, pd.DataFrame] = {}
        unique_values = df[dimension].dropna().unique()

        for val in sorted(unique_values, key=lambda x: str(x)):
            val_str = str(val)
            subset = df[df[dimension] == val]
            sliced_results[val_str] = self.evaluate_funnel(subset)

        return sliced_results

    def run_full_analysis(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Executes comprehensive funnel analysis including overall and all dimensional slices.
        Returns a dictionary suitable for JSON report serialization.
        """
        if df is None:
            df = self.load_data()

        total_sessions = len(df)
        overall_df = self.evaluate_funnel(df)

        overall_records = overall_df.to_dict(orient="records")

        # Find largest drop-off stage
        top_dropoff_stage = None
        max_drop = -1
        for row in overall_records:
            if row["step_number"] > 1 and row["absolute_drop_off"] > max_drop:
                max_drop = row["absolute_drop_off"]
                top_dropoff_stage = row["stage_name"]

        # Dimensional slices
        dim_results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for dim in SLICE_DIMENSIONS:
            if dim in df.columns:
                dim_dict = self.slice_by_dimension(dim, df)
                dim_results[dim] = {
                    val: sub_df.to_dict(orient="records")
                    for val, sub_df in dim_dict.items()
                }

        final_cr = (
            overall_records[-1]["overall_conversion_rate"]
            if overall_records
            else 0.0
        )

        return {
            "total_sessions": total_sessions,
            "overall_conversion_rate": final_cr,
            "top_dropoff_stage": top_dropoff_stage,
            "overall_funnel": overall_records,
            "dimensional_analysis": dim_results,
        }


def compute_funnel_metrics(
    df: pd.DataFrame, sessions_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Convenience function matching conftest oracle style or fact table input.
    If sessions_df is passed, treats df as events_df.
    """
    if sessions_df is not None:
        # Compatibility with oracle_compute_funnel_metrics(events_df, sessions_df)
        analyzer = FunnelAnalyzer(df=df)
        # We can construct a combined dataset or calculate directly
        total_sessions = len(sessions_df)
        event_col = "event_type" if "event_type" in df.columns else "event_name"
        results = []
        prev_count = total_sessions

        for step_num, stage in enumerate(FUNNEL_STAGES, 1):
            reached = (
                df[df[event_col] == stage]["session_id"].nunique()
                if event_col in df.columns
                else 0
            )
            step_conv = (reached / prev_count * 100.0) if prev_count > 0 else 0.0
            overall_conv = (
                (reached / total_sessions * 100.0) if total_sessions > 0 else 0.0
            )
            abs_drop = (
                prev_count - reached if step_num > 1 else total_sessions - reached
            )
            drop_pct = (abs_drop / prev_count * 100.0) if prev_count > 0 else 0.0

            results.append(
                {
                    "step_number": step_num,
                    "stage_name": stage,
                    "sessions_count": int(reached),
                    "step_conversion_rate": round(step_conv, 2),
                    "overall_conversion_rate": round(overall_conv, 2),
                    "absolute_drop_off": int(abs_drop),
                    "drop_off_rate": round(drop_pct, 2),
                }
            )
            prev_count = reached

        return pd.DataFrame(results)

    analyzer = FunnelAnalyzer(df=df)
    return analyzer.evaluate_funnel(df)
