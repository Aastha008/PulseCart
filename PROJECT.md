# Project: PulseCart Analytics Engineering Infrastructure

## Architecture
PulseCart is an end-to-end e-commerce analytics engineering and data science platform modeling customer behavior, funnel drop-offs, cohort retention, and checkout A/B testing across a modern data stack.

```mermaid
flowchart TD
    subgraph S1 [1. Synthetic Data Generation Engine]
        GEN[src/data_generator/generator.py] -->|>=100K Sessions| RAW_DATA[data/raw/*.parquet & *.csv]
        RAW_DATA --> T_USERS[(raw_users)]
        RAW_DATA --> T_SESSIONS[(raw_sessions)]
        RAW_DATA --> T_EVENTS[(raw_events)]
        RAW_DATA --> T_ORDERS[(raw_orders)]
        RAW_DATA --> T_ITEMS[(raw_order_items)]
        RAW_DATA --> T_PRODS[(raw_products)]
    end

    subgraph S2 [2. BigQuery Data Warehouse & dbt Core]
        RAW_DATA --> STG[Staging Layer: stg_* views]
        STG --> INT[Intermediate Layer: int_* views]
        INT --> MARTS[Marts Consumption Layer]
        MARTS --> FCT_F[fct_funnel (Partitioned: session_date)]
        MARTS --> FCT_O[fct_orders (Partitioned: order_date)]
        MARTS --> FCT_R[fct_user_retention (Partitioned: activity_month)]
        MARTS --> FCT_AB[fct_ab_test (Partitioned: session_date)]
        MARTS --> DIM_U[dim_users]
        MARTS --> DIM_P[dim_products]
        MARTS --> DIM_D[dim_date]
    end

    subgraph S3 [3. Statistical Analytics & Experimentation]
        MARTS --> STATS[src/analytics/ab_test.py & runner.py]
        STATS --> STATS_OUT[Multi-stage Funnel, Cohort Retention M0-M6+, SRM Chi2, Two-proportion Z-test, 95% CI]
    end

    subgraph S4 [4. Power BI Semantic Model & Dashboard]
        MARTS --> PBI_MODEL[Star Schema: 4 Facts + 3 Conformed Dims]
        PBI_MODEL --> DAX_LIB[74 DAX Measures: Volume, Financial, Funnel, Retention, Experiment]
        DAX_LIB --> DASH[4-Page Executive Dashboard: Overview, Funnel, Cohorts, A/B Test]
    end

    subgraph S5 [5. Production Orchestration & Repository]
        ORCH[orchestration/daily_pipeline.py] -->|Airflow DAG & Circuit Breaker| S1
        ORCH --> S2
        ORCH --> S3
        ORCH --> S4
        DOCS[docs/ & README.md & Data Dictionary & 5 Interview QA]
    end
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Synthetic User Generation | Deterministic generation of >=25K user profiles with demographic segmentation (VIP, Regular, Bargain), acquisition channels, and creation timestamps | M1 | R1 |
| F02 | Synthetic Product Catalog | 100 conformed products across 5 categories with realistic prices, costs, and margins | M1 | R1 |
| F03 | Synthetic Session Engine | Vectorized generation of >=100K valid browsing sessions across devices, countries, traffic sources | M1 | R1 |
| F04 | Multi-Stage Funnel State Machine | Realistic event sequencing (landing_page -> product_view -> add_to_cart -> checkout_started -> payment_started -> purchase) with dwell times | M1 | R1 |
| F05 | Orthogonal Multiplicative Variance | Transition probability modulation across device, channel, country, segment, and new vs returning users | M1 | R1 |
| F06 | Parameterized Checkout A/B Experiment | 50/50 randomized checkout variant assignment with intended ~8.9% relative lift, zero data fabrication | M1 | R1 |
| F07 | Relational & Temporal Integrity Invariants | Zero orphan records, strict timestamp monotonicity, financial totals reconciliation, CLI generator | M1 | R1 |
| F08 | Raw Warehouse Sources & Schema | Ingestion schemas for raw_users, raw_sessions, raw_events, raw_orders, raw_order_items, raw_products | M2 | R2 |
| F09 | Staging Models (stg_*) | 6 cleaned staging views with normalized types, column renaming, and surrogate keys | M2 | R2 |
| F10 | Intermediate Transformation Models (int_*) | 5 intermediate views modularizing funnel flags, order items aggregation, user lifetime metrics, cohort matrices, and A/B session conversion | M2 | R2 |
| F11 | Mart Fact Tables (fct_*) | Production marts: fct_funnel, fct_orders, fct_user_retention, fct_ab_test | M2 | R2 |
| F12 | Mart Dimension Tables (dim_*) | Conformed dimensions: dim_users, dim_products, dim_date | M2 | R2 |
| F13 | BigQuery Partitioning & Clustering | Daily partitioning on session_date/order_date, monthly on activity_month; multi-column clustering on device_type, country, user_id | M2 | R2 |
| F14 | Incremental Materialization Strategies | Merge incremental strategy with 3-day lookback window for high-volume fact models | M2 | R2 |
| F15 | dbt Generic & Referential Schema Tests | 40+ schema tests covering unique, not_null, accepted_values, and relationships across all PKs and FKs | M2 | R2 |
| F16 | Multi-Stage Funnel Analytics Script | Step volume, stage conversion rate, drop-off rate, dimensional slices across device, channel, country, segment | M3 | R3 |
| F17 | Monthly Cohort Retention Matrix | Cohort assignment, M0-M6+ retention matrices, repeat purchase rates, and segment LTV trajectories | M3 | R3 |
| F18 | A/B Sample Ratio Mismatch (SRM) Test | Pearson's Chi-Square Goodness-of-Fit test (df=1, alpha=0.01) on assignment counts | M3 | R3 |
| F19 | Two-Proportion Z-Test & Confidence Intervals | Hypothesis test (H0: pc = pt), pooled SE, z-score, two-sided p-value, unpooled SE, and Delta Method 95% CI for relative lift | M3 | R3 |
| F20 | Reproducible Python Analytics CLI | Command-line statistical execution runner outputting verified empirical metrics to JSON/CSV/console | M3 | R3 |
| F21 | Star Schema Semantic Model Architecture | 4 fact marts linked to 3 conformed dimensions via 1:* single-direction relationships with role-playing dates | M4 | R4 |
| F22 | Comprehensive DAX Measure Library | 74 production-grade, commented DAX measures across 5 display folders (Volume, Financial, Funnel, Retention, Experiment) | M4 | R4 |
| F23 | 4-Page Executive Dashboard Layout Specs | Pixel-accurate 16:9 UI specifications for Executive Overview, Funnel Analysis, Cohort Retention, and A/B Testing | M4 | R4 |
| F24 | Power BI Reproduction Guide & PBIX Assets | 7-phase step-by-step reproduction guide and automated script generating verified .pbix asset | M4 | R4 |
| F25 | Executive Business Translation & Revenue Impact | C-suite translation separating observed metrics, statistical findings, assumptions, strategic actions, and dual financial impact models | M5 | R5 |
| F26 | Automated Daily Orchestration Pipeline | End-to-end orchestration architecture (Raw -> Warehouse -> dbt -> Tests -> Marts -> Power BI) with hard circuit breaker | M5 | R5 |
| F27 | Production GitHub Repository Deliverables | Clean repo structure, root README.md, Mermaid diagrams, data dictionary, resume-ready bullet points, and 5 technical interview Q&A | M5 | R5 |
| F28 | End-to-End Test Suite & Verification | 4-tier requirement-driven opaque-box test suite (Tiers 1-4) + Tier 5 adversarial hardening | Final | All |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Requirement-driven test harness, test runner, and test suites across Tiers 1-4 | none | DONE |
| M1 | Synthetic Data Generation Engine | R1: >=100K sessions, 6 relational tables, funnel drop-offs, variance vectors, checkout A/B parameterization | none | DONE |
| M2 | BigQuery Warehouse & dbt Modeling | R2: 4-layer dbt project, 18 models (staging, intermediate, marts), partitioning, clustering, 40+ tests | M1 | IN_PROGRESS |
| M3 | Reproducible Analytics & Statistical A/B | R3: Funnel analytics, cohort retention M0-M6+, SRM chi-square test, two-proportion z-test, 95% CI | M1, M2 | PLANNED |
| M4 | Power BI Modeling & DAX Library | R4: Star schema semantic model, 74 DAX measures, 4-page dashboard specs, reproduction guide, verified .pbix | M2, M3 | PLANNED |
| M5 | Production Repo, Orchestration & Translation | R5: Daily orchestration pipeline, circuit breaker, README.md, data dictionary, business translation, resume bullets, 5 Q&A | M1-M4 | PLANNED |
| M_FINAL | Final 100% E2E Verification & Adversarial Hardening | Pass 100% of Tiers 1-4 E2E tests, followed by Tier 5 adversarial stress testing & forensic audit | M1-M5, E2E | PLANNED |

## Interface Contracts

### 1. Synthetic Data Generator -> Warehouse Raw Layer
- Output directory: `data/raw/` (both Parquet and CSV formats).
- Tables and primary keys:
  - `users.parquet`: `user_id` (VARCHAR/UUID PK), `created_at` (TIMESTAMP), `country` (VARCHAR), `acquisition_channel` (VARCHAR), `customer_segment` (VARCHAR).
  - `products.parquet`: `product_id` (VARCHAR PK), `product_name` (VARCHAR), `category` (VARCHAR), `cost` (NUMERIC/FLOAT), `price` (NUMERIC/FLOAT), `margin` (NUMERIC/FLOAT).
  - `sessions.parquet`: `session_id` (VARCHAR PK), `user_id` (VARCHAR FK), `session_start` (TIMESTAMP), `session_end` (TIMESTAMP), `device_type` (VARCHAR), `country` (VARCHAR), `traffic_source` (VARCHAR), `is_bounce` (BOOLEAN), `is_returning_user` (BOOLEAN), `ab_variant` (VARCHAR: 'control'/'treatment').
  - `events.parquet`: `event_id` (VARCHAR PK), `session_id` (VARCHAR FK), `event_timestamp` (TIMESTAMP), `event_name` (VARCHAR: landing_page, product_view, add_to_cart, checkout_started, payment_started, purchase), `step_number` (INTEGER: 1 to 6), `page_url` (VARCHAR), `product_id` (VARCHAR FK, nullable).
  - `orders.parquet`: `order_id` (VARCHAR PK), `session_id` (VARCHAR FK), `user_id` (VARCHAR FK), `order_timestamp` (TIMESTAMP), `subtotal` (FLOAT), `tax_amount` (FLOAT), `shipping_fee` (FLOAT), `discount_amount` (FLOAT), `total_amount` (FLOAT), `payment_method` (VARCHAR), `status` (VARCHAR: 'completed').
  - `order_items.parquet`: `order_item_id` (VARCHAR PK), `order_id` (VARCHAR FK), `product_id` (VARCHAR FK), `quantity` (INTEGER), `unit_price` (FLOAT), `unit_cost` (FLOAT), `line_total` (FLOAT), `line_profit` (FLOAT).
- Constraints: Zero orphan foreign keys. Strict timestamp monotonicity.

### 2. Warehouse Marts -> Python Statistical Engine & Power BI
- Fact marts exported or queried via DuckDB / BigQuery SQL:
  - `fct_funnel`: `session_id`, `user_id`, `session_date`, `device_type`, `country`, `traffic_source`, `customer_segment`, `ab_variant`, `is_returning_user`, `reached_landing_page`, `reached_product_view`, `reached_add_to_cart`, `reached_checkout_started`, `reached_payment_started`, `reached_purchase`, `furthest_step_reached`, `session_duration_seconds`.
  - `fct_orders`: `order_id`, `session_id`, `user_id`, `order_date`, `order_timestamp`, `device_type`, `country`, `traffic_source`, `customer_segment`, `ab_variant`, `item_count`, `subtotal`, `tax_amount`, `shipping_fee`, `discount_amount`, `total_amount`, `total_cost`, `gross_margin_amount`, `is_first_order`.
  - `fct_user_retention`: `user_id`, `cohort_month`, `activity_month`, `month_offset`, `orders_in_month`, `revenue_in_month`, `is_retained`.
  - `fct_ab_test`: `session_id`, `user_id`, `session_date`, `ab_variant`, `device_type`, `country`, `started_checkout`, `completed_payment`, `completed_purchase`.
  - `dim_users`: `user_id`, `first_seen_at`, `acquisition_channel`, `country`, `customer_segment`, `lifetime_sessions`, `lifetime_orders`, `lifetime_revenue`, `first_order_date`, `last_order_date`.
  - `dim_products`: `product_id`, `product_name`, `category`, `cost`, `price`, `margin_amount`, `margin_percentage`.
  - `dim_date`: `date_day`, `year`, `quarter`, `month`, `month_name`, `week_of_year`, `day_of_week`, `day_name`, `is_weekend`.

### 3. Orchestration & Pipeline Execution Contract
- Standard execution commands:
  - Synthetic generation: `python src/data_generator/cli.py --sessions 100000 --seed 42 --output-dir data/raw`
  - dbt build / run / test: `python run_dbt.py run` and `python run_dbt.py test`
  - Statistical analysis: `python src/analytics/statistical_runner.py --output-dir reports/`
  - E2E Test Suite: `pytest tests/e2e/test_suite.py -v`
- Pass/Fail semantics: Exit code 0 indicates success. Any non-zero exit code triggers circuit breaker alerting and halts pipeline.

## Code Layout
```
pulsecart/
├── data/
│   └── raw/                           # Generated Parquet & CSV files (users, sessions, events, orders, order_items, products)
├── dbt_pulsecart/
│   ├── dbt_project.yml                # dbt project configuration
│   ├── profiles.yml                   # BigQuery / DuckDB connection profiles
│   ├── models/
│   │   ├── staging/                   # Staging SQL models & schema.yml
│   │   ├── intermediate/              # Intermediate SQL models & schema.yml
│   │   └── marts/                     # Facts, dimensions & schema.yml
│   └── macros/                        # Compatibility & analytics macros
├── src/
│   ├── data_generator/
│   │   ├── __init__.py
│   │   ├── generator.py               # Vectorized synthetic data generation engine
│   │   ├── schemas.py                 # Pydantic / dataclass schemas & types
│   │   ├── distributions.py           # Multiplicative variance & drop-off models
│   │   └── cli.py                     # CLI entrypoint
│   └── analytics/
│       ├── __init__.py
│       ├── funnel.py                  # Multi-stage funnel analysis
│       ├── retention.py               # Monthly cohort retention matrices
│       ├── ab_test.py                 # Two-proportion z-test, SRM chi-square, 95% CI
│       └── statistical_runner.py      # Master CLI runner
├── power_bi/
│   ├── dax_library.dax                # 74 commented DAX measures
│   ├── dashboard_specifications.md    # 4-page UI/UX specifications
│   ├── semantic_model.json            # Model relationship definitions & metadata
│   ├── reproduction_guide.md          # 7-phase Power BI reproduction manual
│   └── generate_pbix.py               # Automated PBIX generator / validation script
├── orchestration/
│   ├── daily_pipeline.py              # Automated daily ETL & quality gate pipeline
│   ├── airflow_dag.py                 # Production Apache Airflow DAG
│   └── circuit_breaker.py             # Data quality circuit breaker & alerts
├── docs/
│   ├── ARCHITECTURE.md                # System architecture documentation
│   ├── DATA_DICTIONARY.md             # Complete data dictionary for all layers
│   ├── EXECUTIVE_RECOMMENDATIONS.md   # Business translation & incremental revenue models
│   └── INTERVIEW_QA.md                # 5 technical interview scenarios & model answers
├── tests/
│   ├── e2e/                           # Requirement-driven E2E tests (Tiers 1-4)
│   └── unit/                          # Module unit tests
├── README.md                          # Production GitHub repository README
└── run_dbt.py                         # Standalone runner for dbt/DuckDB pipeline
```
