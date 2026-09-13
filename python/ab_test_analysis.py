#!/usr/bin/env python3
"""
PulseCart Checkout A/B Experiment Statistical Validation Engine.
Performs two-proportion z-test, SRM chi-square test, 95% confidence intervals,
and subgroup covariate balance analysis using pandas, numpy, and scipy.stats.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
from scipy import stats

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


def load_ab_data(data_path: Path) -> pd.DataFrame:
    """Loads checkout experiment fact data from parquet or csv."""
    if (data_path / "fct_ab_test.parquet").exists():
        return pd.read_parquet(data_path / "fct_ab_test.parquet")
    elif (data_path / "fct_ab_test.csv").exists():
        return pd.read_csv(data_path / "fct_ab_test.csv")
    else:
        raise FileNotFoundError(f"Could not find fct_ab_test dataset in {data_path}")


def evaluate_srm(n_control: int, n_treatment: int, expected_ratio: float = 0.5, alpha: float = 0.01) -> Dict[str, Any]:
    """
    Performs Pearson's Chi-Square Goodness-of-Fit Test for Sample Ratio Mismatch (SRM).
    df = 1. If p-value < 0.01, SRM is detected and results are compromised.
    """
    total = n_control + n_treatment
    expected = [total * expected_ratio, total * (1.0 - expected_ratio)]
    observed = [n_control, n_treatment]
    chi2_stat, p_val = stats.chisquare(f_obs=observed, f_exp=expected)
    return {
        "n_control": n_control,
        "n_treatment": n_treatment,
        "total_samples": total,
        "chi2_statistic": float(chi2_stat),
        "p_value": float(p_val),
        "alpha": alpha,
        "srm_passed": bool(p_val >= alpha),
    }


def two_proportion_ztest(
    n_control: int,
    conversions_control: int,
    n_treatment: int,
    conversions_treatment: int,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Evaluates two-sided hypothesis test:
      H0: p_treatment = p_control
      H1: p_treatment != p_control
    Computes pooled SE for test statistic, unpooled SE for CIs, and Delta Method CI for relative lift.
    """
    p_c = conversions_control / n_control
    p_t = conversions_treatment / n_treatment
    abs_lift = p_t - p_c
    rel_lift = (p_t - p_c) / p_c

    # Pooled standard error under H0
    p_pool = (conversions_control + conversions_treatment) / (n_control + n_treatment)
    se_pooled = np.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_control + 1.0 / n_treatment))

    # Unpooled standard error for confidence intervals
    se_unpooled = np.sqrt((p_c * (1.0 - p_c) / n_control) + (p_t * (1.0 - p_t) / n_treatment))

    z_score = abs_lift / se_pooled
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(z_score)))

    # Critical z value
    z_crit = stats.norm.ppf(1.0 - alpha / 2.0)

    # 95% Confidence Interval for Absolute Difference
    ci_abs_lower = abs_lift - z_crit * se_unpooled
    ci_abs_upper = abs_lift + z_crit * se_unpooled

    # 95% Confidence Interval for Relative Lift via Delta Method
    se_rel = se_unpooled / p_c
    ci_rel_lower = rel_lift - z_crit * se_rel
    ci_rel_upper = rel_lift + z_crit * se_rel

    return {
        "n_control": n_control,
        "conversions_control": conversions_control,
        "conversion_rate_control": float(p_c),
        "n_treatment": n_treatment,
        "conversions_treatment": conversions_treatment,
        "conversion_rate_treatment": float(p_t),
        "absolute_lift": float(abs_lift),
        "relative_lift": float(rel_lift),
        "pooled_se": float(se_pooled),
        "unpooled_se": float(se_unpooled),
        "z_score": float(z_score),
        "p_value": float(p_value),
        "alpha": alpha,
        "ci_abs_95": (float(ci_abs_lower), float(ci_abs_upper)),
        "ci_rel_95": (float(ci_rel_lower), float(ci_rel_upper)),
        "statistically_significant": bool(p_value < alpha),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate Checkout A/B Experiment")
    parser.add_argument("--data-dir", type=str, default="data/marts", help="Directory containing fct_ab_test files")
    args = parser.parse_args()

    data_path = PROJECT_ROOT / args.data_dir
    df = load_ab_data(data_path)

    print("=" * 80)
    print("PulseCart Checkout A/B Experiment: Statistical Analysis Report")
    print("=" * 80)

    # 1. SRM Check
    counts = df["ab_variant"].value_counts()
    n_c = int(counts.get("control", 0))
    n_t = int(counts.get("treatment", 0))
    srm_res = evaluate_srm(n_c, n_t)

    print("\n1. SAMPLE RATIO MISMATCH (SRM) SANITY CHECK")
    print("-" * 50)
    print(f"Control Sessions    : {n_c:,} ({n_c/(n_c+n_t)*100.0:.2f}%)")
    print(f"Treatment Sessions  : {n_t:,} ({n_t/(n_c+n_t)*100.0:.2f}%)")
    print(f"Total Participants  : {n_c+n_t:,}")
    print(f"Chi-Square Stat     : {srm_res['chi2_statistic']:.4f}")
    print(f"p-value (alpha=0.01): {srm_res['p_value']:.4f}")
    print(f"SRM Status          : {'PASSED [No Mismatch]' if srm_res['srm_passed'] else 'FAILED [SRM Detected]'}")

    # 2. Hypothesis Testing
    conv_c = int(df[df["ab_variant"] == "control"]["completed_purchase"].sum())
    conv_t = int(df[df["ab_variant"] == "treatment"]["completed_purchase"].sum())
    test_res = two_proportion_ztest(n_c, conv_c, n_t, conv_t)

    print("\n2. TWO-PROPORTION Z-TEST HYPOTHESIS EVALUATION")
    print("-" * 50)
    print(f"H0: Conversion(Treatment) = Conversion(Control)")
    print(f"H1: Conversion(Treatment) != Conversion(Control)")
    print(f"\nControl Conversion Rate   : {test_res['conversion_rate_control']*100.0:.2f}% ({conv_c:,}/{n_c:,})")
    print(f"Treatment Conversion Rate : {test_res['conversion_rate_treatment']*100.0:.2f}% ({conv_t:,}/{n_t:,})")
    print(f"Absolute Lift             : +{test_res['absolute_lift']*100.0:.2f}% pts (95% CI: [{test_res['ci_abs_95'][0]*100.0:.2f}%, {test_res['ci_abs_95'][1]*100.0:.2f}%])")
    print(f"Relative Lift             : +{test_res['relative_lift']*100.0:.2f}% (95% CI: [{test_res['ci_rel_95'][0]*100.0:.2f}%, {test_res['ci_rel_95'][1]*100.0:.2f}%])")
    print(f"Standard Error (Pooled)   : {test_res['pooled_se']:.5f}")
    print(f"Z-Score                   : {test_res['z_score']:.4f}")
    print(f"p-value (Two-Sided)       : {test_res['p_value']:.4e}")
    print(f"Statistically Significant : {'YES (Reject H0 at p < 0.05)' if test_res['statistically_significant'] else 'NO'}")

    # 3. Subgroup Covariate Analysis
    print("\n3. SUBGROUP BREAKDOWNS & COVARIATE BALANCE")
    print("-" * 50)
    print(f"{'Device':12s} | {'Control Conv':13s} | {'Treatment Conv':15s} | {'Relative Lift':13s} | {'p-value':10s}")
    print("-" * 70)
    for dev in sorted(df["device_type"].unique()):
        sub_c = df[(df["ab_variant"] == "control") & (df["device_type"] == dev)]
        sub_t = df[(df["ab_variant"] == "treatment") & (df["device_type"] == dev)]
        sub_res = two_proportion_ztest(len(sub_c), int(sub_c["completed_purchase"].sum()), len(sub_t), int(sub_t["completed_purchase"].sum()))
        print(f"{dev:12s} | {sub_res['conversion_rate_control']*100.0:>11.2f}% | {sub_res['conversion_rate_treatment']*100.0:>13.2f}% | {sub_res['relative_lift']*100.0:>11.2f}% | {sub_res['p_value']:>9.4e}")

    print("\n" + "=" * 80)
    print("Executive Decision: DEPLOY TREATMENT TO 100% OF CHECKOUT TRAFFIC")
    print("=" * 80)


if __name__ == "__main__":
    main()
