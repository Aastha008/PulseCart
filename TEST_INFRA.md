# PulseCart E2E Test Infrastructure & Methodology (`TEST_INFRA.md`)

**Document Version**: 1.0.0  
**Architect**: E2E Test Suite Architect (`test_writer_e2e_1`)  
**Date**: 2026-09-06  
**Status**: COMPLETE & VERIFIED  
**Target Repository**: `C:/Users/hp/.gemini/antigravity/scratch/pulsecart/`  
**Integrity Mode**: Benchmark (Strict empirical computation, zero fabricated data, reproducible engineering)

---

## 1. Executive Summary & Testing Philosophy

PulseCart is an enterprise-grade analytics engineering infrastructure platform integrating synthetic behavioral data generation (R1), BigQuery/dbt 4-layer dimensional warehousing (R2), reproducible statistical analytics & A/B testing (R3), Power BI semantic modeling with 74 DAX measures (R4), and automated daily orchestration with data quality circuit breakers (R5).

The PulseCart End-to-End (E2E) Test Suite is designed with a **requirement-driven, opaque-box testing methodology**:
1. **Opaque-Box Independence**: Tests evaluate the system strictly via public interfaces, CLI entrypoints, schema definitions, SQL query results, and empirical file outputs (`.parquet`, `.csv`, `.sql`, `.dax`, `.json`, `.md`). Tests never couple to private internal implementation methods.
2. **Empirical Ground Truth (Zero Fabrication)**: All expected values derive strictly from formal mathematical proofs, relational invariants, and authoritative requirements documented in `ORIGINAL_REQUEST.md` and `PROJECT.md`. No hardcoded mock assertions or facade tests.
3. **Progressive Testability & Self-Containment**: Every test module is self-contained. Using portable embedded DuckDB and Pandas/SciPy engines, the test harness can validate schemas, SQL transformations, invariants, and statistical mechanics independently of external cloud credentials.
4. **Hierarchical 4-Tier Test Structure**:
   - **Tier 1: Feature Coverage**: Comprehensive happy-path coverage verifying core functionality for all 28 project features ($\ge 5$ test cases per feature).
   - **Tier 2: Boundary & Corner Cases**: Exhaustive edge case, extreme boundary, null value, zero-division, and overflow testing for all 28 features ($\ge 5$ test cases per feature).
   - **Tier 3: Cross-Feature Combinations**: Pairwise and multi-dimensional interactions across tables, stages, models, dimensions, and operational pipelines.
   - **Tier 4: Real-World Application Scenarios**: Multi-step, end-to-end operational workflows mirroring production e-commerce operations from data generation to executive decision-making.

---

## 2. Test Suite Architecture & Directory Layout

The test suite is structured cleanly under `tests/e2e/` alongside unit tests in `tests/unit/`:

```
pulsecart/
├── tests/
│   ├── conftest.py                    # Root pytest configuration
│   ├── e2e/                           # End-to-End Test Suite Track
│   │   ├── __init__.py
│   │   ├── conftest.py                # Shared fixtures, DuckDB harness, synthetic fixtures & oracles
│   │   ├── test_tier1_features.py     # Tier 1: Feature Coverage (>=5 tests per feature F01-F28)
│   │   ├── test_tier2_boundaries.py   # Tier 2: Boundary & Corner Cases (>=5 tests per feature F01-F28)
│   │   ├── test_tier3_combinations.py # Tier 3: Cross-Feature Combinations & Pairwise Interactions
│   │   └── test_tier4_scenarios.py    # Tier 4: Real-World Operational Scenarios (5 Workflows)
│   └── unit/                          # Component-level unit tests
├── TEST_INFRA.md                      # This document: Testing architecture & methodology
└── TEST_READY.md                      # Execution guide, test inventory & readiness matrix
```

---

## 3. Four-Tier Testing Methodology

### Tier 1: Feature Coverage (Happy Path)
- **Objective**: Ensure every discrete requirement and feature from F01 to F28 performs its core function under valid conditions.
- **Threshold**: $\ge 5$ distinct test cases per feature ($28 \times 5 = 140$ tests minimum).
- **Scope**:
  - `F01 - F07`: Synthetic Data Engine (user demographics, product catalog, sessions, funnel state machine, multiplicative variance, A/B assignment, 7 relational invariants).
  - `F08 - F15`: Warehouse & dbt Modeling (raw ingestion schemas, staging views, intermediate models, marts facts and dimensions, partitioning, clustering, incremental merge, dbt schema tests).
  - `F16 - F20`: Statistical Analytics & Experimentation (funnel analytics, M0-M6 cohort retention, SRM chi-square test, two-proportion z-test with 95% CI, CLI runner).
  - `F21 - F24`: Power BI Semantic Model & DAX (star schema topology, 74 DAX measures, 4-page dashboard specifications, reproduction guide and PBIX generation).
  - `F25 - F28`: Business Translation, Orchestration & Production Repo (executive recommendations, daily orchestration pipeline, GitHub repository deliverables, end-to-end verification).

### Tier 2: Boundary & Corner Cases
- **Objective**: Stress-test the system against extreme values, boundary conditions, zero inputs, empty collections, division by zero, null fields, and out-of-order execution.
- **Threshold**: $\ge 5$ distinct edge case tests per feature ($28 \times 5 = 140$ tests minimum).
- **Scope**:
  - Zero session volumes, empty raw tables, single-user cohorts.
  - Zero conversions in Control or Treatment variants (protecting against `#DIV/0!`).
  - Extreme sample ratio mismatches ($\chi^2 \gg 6.635$).
  - Clamping of multiplicative probabilities to $[0.05, 0.98]$.
  - Sub-cent financial rounding tolerances ($|\Delta| < 0.01$).
  - Negative values in prices, margins, quantities, or durations.
  - Calendar boundary rollovers (leap days, month-length variance, timezone offsets).
  - Circuit breaker hard halt under corrupt foreign key injection.

### Tier 3: Cross-Feature Combinations
- **Objective**: Verify seamless interoperability across modular boundaries, data pipelines, and analytical interfaces.
- **Key Interaction Vectors**:
  1. *Variance $\times$ Funnel Progression*: Interaction of 3 devices $\times$ 6 channels $\times$ 6 countries $\times$ 3 segments with 6 sequential funnel drop-off stages.
  2. *Funnel Completion $\times$ Order Financial Reconciliation*: Matching completed `purchase` events to `orders` and `order_items`, verifying $Subtotal = \sum (\text{Price} \times \text{Qty})$ and $Total = Subtotal + Tax + Shipping - Discount$.
  3. *A/B Variant $\times$ Cohort Month Retention*: Tracking whether Treatment vs Control sessions convert at different rates and how their downstream repeat purchase rates mature across monthly cohorts.
  4. *Staging $\to$ Intermediate $\to$ Marts Fact Lineage*: Tracing raw clickstream events through `stg_events`, `int_session_funnel_events`, and `fct_funnel`, verifying flag consistency and surrogate key integrity.
  5. *Star Schema $\times$ DAX Evaluation*: Slicing fact measures (`fct_orders`, `fct_funnel`) across conformed dimensions (`dim_users`, `dim_products`, `dim_date`) under active and inactive date relationships.
  6. *Orchestration Circuit Breakers $\times$ Automated Retries*: Verifying that failures in upstream staging models halt downstream marts and prevent corrupted dataset refreshes.

### Tier 4: Real-World Application Scenarios
- **Objective**: Validate complete, end-to-end realistic operational workflows from initiation to executive consumption.
- **5 Comprehensive Scenarios**:
  1. **Scenario 1: Full DTC E-Commerce Daily Operational Lifecycle**
     - Execution of synthetic generator producing 100K+ sessions.
     - Loading into DuckDB/BigQuery staging views, intermediate aggregations, and marts tables.
     - Execution of statistical analytics runner generating funnel reports, cohort matrices, and A/B test summaries.
     - Automated validation of report outputs and financial reconciliations.
  2. **Scenario 2: High-Traffic Promotional Flash Sale Surge**
     - Simulation of promotional campaign: VIP user volume spikes ($3\times$), mobile traffic skew ($75\%$), basket size discounts ($20\%$).
     - Multi-item order creation, tax scaling, free shipping threshold verification ($Total > \$100 \implies Shipping = \$0$).
     - Marts gross margin and profitability aggregation.
  3. **Scenario 3: End-to-End Checkout A/B Experiment Decision Lifecycle**
     - Balanced 50/50 randomized traffic exposure at `checkout_started`.
     - Sample Ratio Mismatch (SRM) Pearson Chi-Square verification ($\alpha = 0.01$).
     - Two-proportion hypothesis test ($H_0: p_C = p_T$ vs $H_1: p_C \ne p_T$) calculating pooled standard error, $Z$-score, and two-sided $p$-value.
     - Delta Method 95% Confidence Interval computation for relative lift.
     - Automated executive decision engine recommending feature rollout with incremental revenue projection.
  4. **Scenario 4: Multi-Month Cohort Retention & Customer LTV Maturation**
     - Cohort assignment by maiden purchase month ($M_0$).
     - Multi-month activity tracking ($M_0$ through $M_6+$).
     - Repeat Purchase Rate (RPR) calculation.
     - Customer segment cumulative LTV curve progression.
  5. **Scenario 5: Operational Incident, Circuit Breaker Trip & Resilient Recovery**
     - Deliberate injection of referential integrity violation (orphan order with nonexistent `session_id`).
     - Automated schema test failure detection (`dbt test`).
     - Hard pipeline abort, halting marts build and Power BI refresh.
     - Incident webhook alert dispatch (`#data-ops-alerts`).
     - Data cleansing, pipeline re-run, and clean verification.

---

## 4. Authoritative Verification Oracles & Mathematical Formats

All test expectations derive from explicit mathematical formulas:

### 1. Funnel Metrics
- Step Conversion Rate: $CR_{k \mid k-1} = \frac{N_k}{N_{k-1}} \times 100\%$
- Overall Funnel Conversion Rate: $CR_{\text{overall}} = \frac{N_6}{N_1} \times 100\%$
- Absolute Drop-Off: $D_k^{\text{abs}} = N_{k-1} - N_k$
- Step Drop-Off Rate: $D_k^{\%} = \frac{N_{k-1} - N_k}{N_{k-1}} \times 100\% = 100\% - CR_{k \mid k-1}$

### 2. Multiplicative Probability Modulation
$$p_{k, i} = \text{clip}\left( p_{\text{base}, k} \times \prod_{d \in \text{Dimensions}} \omega_{d, k}, \; 0.05, \; 0.98 \right)$$
Where $\omega_d$ includes device, channel, country, customer segment, and user type multipliers.

### 3. A/B Sample Ratio Mismatch (SRM)
$$\chi^2 = \frac{(O_C - E_C)^2}{E_C} + \frac{(O_T - E_T)^2}{E_T}, \quad E_C = E_T = \frac{N}{2}$$
Decision: If $p_{\text{SRM}} = 1 - F_{\chi^2_1}(\chi^2) < 0.01 \implies$ SRM detected (fail); else pass.

### 4. Two-Proportion Z-Test & Confidence Intervals
- Pooled Proportion: $\hat{p}_{\text{pool}} = \frac{X_C + X_T}{n_C + n_T}$
- Pooled SE: $SE_{\text{pool}} = \sqrt{\hat{p}_{\text{pool}}(1 - \hat{p}_{\text{pool}}) \left( \frac{1}{n_C} + \frac{1}{n_T} \right)}$
- Test Statistic: $Z = \frac{\hat{p}_T - \hat{p}_C}{SE_{\text{pool}}}$
- Two-Sided P-Value: $p = 2 \times (1 - \Phi(|Z|))$
- Unpooled SE: $SE_{\Delta} = \sqrt{\frac{\hat{p}_C(1 - \hat{p}_C)}{n_C} + \frac{\hat{p}_T(1 - \hat{p}_T)}{n_T}}$
- 95% CI for Absolute Difference: $[\Delta \pm 1.95996 \cdot SE_{\Delta}]$
- 95% CI for Relative Lift (Delta Method): $\left[ \frac{\Delta \pm 1.95996 \cdot SE_{\Delta}}{\hat{p}_C} \right]$

### 5. Relational & Financial Invariants
1. $Subtotal = \sum (\text{unit\_price} \times \text{quantity})$
2. $Total = Subtotal + Tax + Shipping - Discount$
3. Monotonic Timestamps: $T_{\text{user}} \le T_{\text{session\_start}} \le T_{\text{event\_1}} < \dots < T_{\text{event\_k}} = T_{\text{order}} \le T_{\text{session\_end}}$
4. 1:1 Correspondence: $N(\text{events with event\_name='purchase'}) == N(\text{orders})$
5. Zero Orphan FKs: $\forall s \in \text{sessions}: s.\text{user\_id} \in \text{users}.\text{user\_id}$

---

## 5. Test Execution Harness & Pytest Commands

### Prerequisites
- Python $\ge 3.10$
- Dependencies: `pytest`, `pandas`, `numpy`, `scipy`, `duckdb`, `pyarrow`

### Standard Invocation Commands
```bash
# Run entire E2E test suite across all 4 tiers
pytest tests/e2e/ -v

# Run specific tier suites
pytest tests/e2e/test_tier1_features.py -v
pytest tests/e2e/test_tier2_boundaries.py -v
pytest tests/e2e/test_tier3_combinations.py -v
pytest tests/e2e/test_tier4_scenarios.py -v

# Run filtered by feature marker (e.g. F06 A/B testing)
pytest tests/e2e/ -v -k "f06"

# Run with fail-fast on first error
pytest tests/e2e/ -v -x

# Generate JUnit XML test report for CI/CD
pytest tests/e2e/ --junitxml=reports/e2e_results.xml
```

---

## 6. Traceability Matrix (Requirements $\to$ Features $\to$ Tests)

| Requirement | Feature ID | Feature Name | Tier 1 Tests | Tier 2 Tests | Tier 3 Tests | Tier 4 Scenarios |
|---|---|---|---|---|---|---|
| R1 | F01 | Synthetic User Generation | `test_f01_*` (5) | `test_f01_bnd_*` (5) | Yes | S1, S2 |
| R1 | F02 | Synthetic Product Catalog | `test_f02_*` (5) | `test_f02_bnd_*` (5) | Yes | S1, S2 |
| R1 | F03 | Synthetic Session Engine | `test_f03_*` (5) | `test_f03_bnd_*` (5) | Yes | S1, S2, S3 |
| R1 | F04 | Multi-Stage Funnel State Machine | `test_f04_*` (5) | `test_f04_bnd_*` (5) | Yes | S1, S2, S3 |
| R1 | F05 | Orthogonal Multiplicative Variance | `test_f05_*` (5) | `test_f05_bnd_*` (5) | Yes | S1, S2 |
| R1 | F06 | Parameterized Checkout A/B Experiment | `test_f06_*` (5) | `test_f06_bnd_*` (5) | Yes | S3 |
| R1 | F07 | Relational & Temporal Integrity Invariants | `test_f07_*` (5) | `test_f07_bnd_*` (5) | Yes | S1, S5 |
| R2 | F08 | Raw Warehouse Sources & Schema | `test_f08_*` (5) | `test_f08_bnd_*` (5) | Yes | S1, S5 |
| R2 | F09 | Staging Models (stg_*) | `test_f09_*` (5) | `test_f09_bnd_*` (5) | Yes | S1, S5 |
| R2 | F10 | Intermediate Transformation Models (int_*) | `test_f10_*` (5) | `test_f10_bnd_*` (5) | Yes | S1 |
| R2 | F11 | Mart Fact Tables (fct_*) | `test_f11_*` (5) | `test_f11_bnd_*` (5) | Yes | S1, S3, S4 |
| R2 | F12 | Mart Dimension Tables (dim_*) | `test_f12_*` (5) | `test_f12_bnd_*` (5) | Yes | S1 |
| R2 | F13 | BigQuery Partitioning & Clustering | `test_f13_*` (5) | `test_f13_bnd_*` (5) | Yes | S1 |
| R2 | F14 | Incremental Materialization Strategies | `test_f14_*` (5) | `test_f14_bnd_*` (5) | Yes | S1 |
| R2 | F15 | dbt Generic & Referential Schema Tests | `test_f15_*` (5) | `test_f15_bnd_*` (5) | Yes | S1, S5 |
| R3 | F16 | Multi-Stage Funnel Analytics Script | `test_f16_*` (5) | `test_f16_bnd_*` (5) | Yes | S1, S2 |
| R3 | F17 | Monthly Cohort Retention Matrix | `test_f17_*` (5) | `test_f17_bnd_*` (5) | Yes | S1, S4 |
| R3 | F18 | A/B Sample Ratio Mismatch (SRM) Test | `test_f18_*` (5) | `test_f18_bnd_*` (5) | Yes | S3 |
| R3 | F19 | Two-Proportion Z-Test & Confidence Intervals | `test_f19_*` (5) | `test_f19_bnd_*` (5) | Yes | S3 |
| R3 | F20 | Reproducible Python Analytics CLI | `test_f20_*` (5) | `test_f20_bnd_*` (5) | Yes | S1, S3 |
| R4 | F21 | Star Schema Semantic Model Architecture | `test_f21_*` (5) | `test_f21_bnd_*` (5) | Yes | S1 |
| R4 | F22 | Comprehensive DAX Measure Library | `test_f22_*` (5) | `test_f22_bnd_*` (5) | Yes | S1, S3 |
| R4 | F23 | 4-Page Executive Dashboard Layout Specs | `test_f23_*` (5) | `test_f23_bnd_*` (5) | Yes | S1 |
| R4 | F24 | Power BI Reproduction Guide & PBIX Assets | `test_f24_*` (5) | `test_f24_bnd_*` (5) | Yes | S1 |
| R5 | F25 | Executive Business Translation & Revenue Impact | `test_f25_*` (5) | `test_f25_bnd_*` (5) | Yes | S3 |
| R5 | F26 | Automated Daily Orchestration Pipeline | `test_f26_*` (5) | `test_f26_bnd_*` (5) | Yes | S1, S5 |
| R5 | F27 | Production GitHub Repository Deliverables | `test_f27_*` (5) | `test_f27_bnd_*` (5) | Yes | S1 |
| R5 | F28 | End-to-End Test Suite & Verification | `test_f28_*` (5) | `test_f28_bnd_*` (5) | Yes | S1-S5 |
