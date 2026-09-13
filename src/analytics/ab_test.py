"""
PulseCart A/B Testing & Statistical Experimentation Engine
Features F18, F19 / Milestone 3

Implements:
1. Sample Ratio Mismatch (SRM) balance check using Pearson's Chi-Square Goodness-of-Fit (df=1, alpha=0.01).
2. Two-Proportion Z-Test for checkout conversion rates (H0: pt = pc vs H1: pt != pc).
3. Pooled standard error, z-score, two-sided p-value.
4. 95% Confidence Intervals for absolute risk difference and Delta Method 95% CI for relative lift.
5. Dimension-level experimental breakdown across device_type and country.
"""

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class SRMResult:
    n_control: int
    n_treatment: int
    total_samples: int
    expected_ratio: float
    chi2_statistic: float
    p_value: float
    alpha: float
    srm_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ABTestResult:
    n_control: int
    conversions_control: int
    conversion_rate_control: float
    n_treatment: int
    conversions_treatment: int
    conversion_rate_treatment: float
    absolute_difference: float
    relative_lift: float
    pooled_se: float
    z_score: float
    p_value: float
    alpha: float
    ci_abs_lower: float
    ci_abs_upper: float
    ci_rel_lower: float
    ci_rel_upper: float
    statistically_significant: bool
    srm: Optional[SRMResult] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.srm:
            d["srm"] = self.srm.to_dict()
        return d


def compute_srm_test(
    n_ctrl: int, n_treat: int, p: float = 0.5, alpha: float = 0.01
) -> SRMResult:
    """
    Pearson Chi-Square Goodness-of-Fit test for Sample Ratio Mismatch (SRM).
    df = 1, default alpha = 0.01.
    """
    total = n_ctrl + n_treat
    if total == 0:
        return SRMResult(
            n_control=0,
            n_treatment=0,
            total_samples=0,
            expected_ratio=p,
            chi2_statistic=0.0,
            p_value=1.0,
            alpha=alpha,
            srm_passed=True,
        )

    e_ctrl = total * p
    e_treat = total * (1.0 - p)

    if e_ctrl == 0 or e_treat == 0:
        chi2 = 999.0
        p_val = 0.0
        srm_passed = False
    else:
        chi2 = ((n_ctrl - e_ctrl) ** 2) / e_ctrl + ((n_treat - e_treat) ** 2) / e_treat
        p_val = float(1.0 - stats.chi2.cdf(chi2, df=1))
        srm_passed = bool(p_val >= alpha)

    return SRMResult(
        n_control=int(n_ctrl),
        n_treatment=int(n_treat),
        total_samples=int(total),
        expected_ratio=float(p),
        chi2_statistic=float(chi2),
        p_value=float(p_val),
        alpha=float(alpha),
        srm_passed=bool(srm_passed),
    )


def compute_two_proportion_ztest(
    n_ctrl: int,
    conv_ctrl: int,
    n_treat: int,
    conv_treat: int,
    alpha: float = 0.05,
) -> ABTestResult:
    """
    Two-proportion hypothesis test for difference in binomial proportions.
    Calculates pooled SE, z-score, two-sided p-value, and Delta Method 95% CI.
    """
    p_c = conv_ctrl / n_ctrl if n_ctrl > 0 else 0.0
    p_t = conv_treat / n_treat if n_treat > 0 else 0.0
    abs_diff = p_t - p_c
    rel_lift = (p_t - p_c) / p_c if p_c > 0 else 0.0

    # Pooled standard error under H0
    if (n_ctrl + n_treat) > 0:
        p_pool = (conv_ctrl + conv_treat) / (n_ctrl + n_treat)
    else:
        p_pool = 0.0

    if n_ctrl > 0 and n_treat > 0 and 0.0 < p_pool < 1.0:
        se_pool = float(
            np.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_ctrl + 1.0 / n_treat))
        )
    else:
        se_pool = 0.0

    z_score = float(abs_diff / se_pool) if se_pool > 0 else 0.0
    p_value = float(2.0 * (1.0 - stats.norm.cdf(abs(z_score))))

    # Unpooled standard error for confidence intervals
    if n_ctrl > 0 and n_treat > 0:
        se_unpooled = float(
            np.sqrt(
                (p_c * (1.0 - p_c) / n_ctrl) + (p_t * (1.0 - p_t) / n_treat)
            )
        )
    else:
        se_unpooled = 0.0

    z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
    ci_abs_lower = float(abs_diff - z_crit * se_unpooled)
    ci_abs_upper = float(abs_diff + z_crit * se_unpooled)

    # Delta method for relative lift CI
    ci_rel_lower = float(ci_abs_lower / p_c) if p_c > 0 else 0.0
    ci_rel_upper = float(ci_abs_upper / p_c) if p_c > 0 else 0.0

    srm_res = compute_srm_test(n_ctrl, n_treat, p=0.5, alpha=0.01)

    return ABTestResult(
        n_control=int(n_ctrl),
        conversions_control=int(conv_ctrl),
        conversion_rate_control=float(p_c),
        n_treatment=int(n_treat),
        conversions_treatment=int(conv_treat),
        conversion_rate_treatment=float(p_t),
        absolute_difference=float(abs_diff),
        relative_lift=float(rel_lift),
        pooled_se=float(se_pool),
        z_score=float(z_score),
        p_value=float(p_value),
        alpha=float(alpha),
        ci_abs_lower=float(ci_abs_lower),
        ci_abs_upper=float(ci_abs_upper),
        ci_rel_lower=float(ci_rel_lower),
        ci_rel_upper=float(ci_rel_upper),
        statistically_significant=bool(p_value < alpha),
        srm=srm_res,
    )


class ABTestAnalyzer:
    """A/B experiment processor evaluating checkout conversion rates."""

    def __init__(
        self,
        data_path: Optional[Union[str, Path]] = None,
        df: Optional[pd.DataFrame] = None,
    ):
        self.data_path = Path(data_path) if data_path else None
        self._df = df.copy() if df is not None else None

    def load_data(self) -> pd.DataFrame:
        """Loads fct_ab_test data with Parquet preference and CSV fallback."""
        if self._df is not None:
            return self._df

        if self.data_path is not None:
            candidates = [self.data_path]
            if self.data_path.suffix == ".parquet":
                candidates.append(self.data_path.with_suffix(".csv"))
            elif self.data_path.suffix == ".csv":
                candidates.insert(0, self.data_path.with_suffix(".parquet"))
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "marts"
            candidates = [
                base_dir / "fct_ab_test.parquet",
                base_dir / "fct_ab_test.csv",
            ]

        for p in candidates:
            if p.exists():
                try:
                    if p.suffix == ".parquet":
                        logger.info(f"Loading A/B test data from {p}")
                        self._df = pd.read_parquet(p)
                    else:
                        logger.info(f"Loading A/B test data from CSV fallback {p}")
                        self._df = pd.read_csv(p)
                    return self._df
                except Exception as e:
                    logger.warning(f"Failed to read {p}: {e}")

        raise FileNotFoundError(
            f"Could not load A/B test dataset from any candidate path: {[str(p) for p in candidates]}"
        )

    def evaluate_experiment(
        self, df: Optional[pd.DataFrame] = None, alpha: float = 0.05
    ) -> ABTestResult:
        """
        Calculates SRM, Two-Proportion Z-Test, and Confidence Intervals.
        """
        if df is None:
            df = self.load_data()

        if len(df) == 0:
            return compute_two_proportion_ztest(0, 0, 0, 0, alpha=alpha)

        # Variant column detection
        variant_col = "ab_variant" if "ab_variant" in df.columns else "variant"
        if variant_col not in df.columns:
            raise KeyError(f"Expected variant column in dataset: {df.columns}")

        # Conversion column detection
        conv_col = None
        for candidate in ["completed_purchase", "converted_to_purchase", "is_converting_session", "reached_purchase"]:
            if candidate in df.columns:
                conv_col = candidate
                break

        if not conv_col:
            raise KeyError("No purchase conversion column found in A/B test dataset.")

        ctrl_df = df[df[variant_col] == "control"]
        treat_df = df[df[variant_col] == "treatment"]

        n_ctrl = len(ctrl_df)
        n_treat = len(treat_df)

        conv_ctrl = int((ctrl_df[conv_col].astype(int) > 0).sum())
        conv_treat = int((treat_df[conv_col].astype(int) > 0).sum())

        return compute_two_proportion_ztest(
            n_ctrl=n_ctrl,
            conv_ctrl=conv_ctrl,
            n_treat=n_treat,
            conv_treat=conv_treat,
            alpha=alpha,
        )

    def slice_by_dimension(
        self, dimension: str, df: Optional[pd.DataFrame] = None, alpha: float = 0.05
    ) -> Dict[str, ABTestResult]:
        """
        Runs A/B test analysis broken down by values of a dimension (e.g., device_type, country).
        """
        if df is None:
            df = self.load_data()

        if dimension not in df.columns:
            logger.warning(f"Dimension '{dimension}' not present in dataset.")
            return {}

        results: Dict[str, ABTestResult] = {}
        unique_vals = df[dimension].dropna().unique()

        for val in sorted(unique_vals, key=lambda x: str(x)):
            sub_df = df[df[dimension] == val]
            results[str(val)] = self.evaluate_experiment(sub_df, alpha=alpha)

        return results

    def run_full_analysis(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Executes complete A/B experiment evaluation including overall and dimensional breakdowns.
        """
        if df is None:
            df = self.load_data()

        overall_result = self.evaluate_experiment(df)

        # Dimensional cuts
        by_device = self.slice_by_dimension("device_type", df)
        by_country = self.slice_by_dimension("country", df)

        return {
            "experiment_name": "checkout_optimization",
            "target_relative_lift": 0.089,
            "overall_results": overall_result.to_dict(),
            "by_device": {k: res.to_dict() for k, res in by_device.items()},
            "by_country": {k: res.to_dict() for k, res in by_country.items()},
        }


def compute_ab_test(
    df: pd.DataFrame, alpha: float = 0.05
) -> Dict[str, Any]:
    """Convenience helper to compute A/B test results from DataFrame."""
    analyzer = ABTestAnalyzer(df=df)
    return analyzer.run_full_analysis(df)
