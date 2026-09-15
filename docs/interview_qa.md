# PulseCart Technical Interview Preparation: 5 Senior-Level Scenarios & Model Answers

This document provides 5 rigorous, production-grade technical interview questions based directly on the PulseCart analytics engineering and experimentation architecture, complete with senior-level model responses.

---

### Question 1: How do you detect and handle Sample Ratio Mismatch (SRM) in e-commerce A/B testing, and why is it dangerous to ignore?

**Model Answer:**
> "Sample Ratio Mismatch (SRM) occurs when the observed ratio of visitors assigned to experimental variants deviates statistically from the intended allocation design (typically 50/50). 
>
> In PulseCart, we test for SRM before evaluating any primary business metrics by running **Pearson's Chi-Square Goodness-of-Fit Test** with 1 degree of freedom:
>
> $$\chi^2 = \sum \frac{(O_i - E_i)^2}{E_i} = \frac{(N_c - E)^2}{E} + \frac{(N_t - E)^2}{E}$$
>
> where $E = \frac{N_c + N_t}{2}$. We evaluate this at a conservative significance threshold of $\alpha = 0.01$ (critical value $\chi^2 = 6.635$). In our checkout test of 16,430 participants ($N_c = 8,151$, $N_t = 8,279$), the observed statistic was $\chi^2 = 0.9972$ with a $p$-value of $0.3180$, confirming no SRM.
>
> **Why SRM is dangerous:**
> Ignoring SRM introduces severe selection bias. If an experiment suffers from SRM, the two variants no longer have identical underlying population distributions. For instance, if the treatment variant caused JavaScript crashes on older Android mobile devices, those users drop out before logging an assignment event. The treatment group would artificially appear to have higher conversion simply because low-converting mobile users were systematically filtered out. 
>
> **Resolution Protocol:**
> 1. Immediately pause the experiment and refuse to report conversion lift.
> 2. Conduct a root-cause breakdown across traffic sources, browsers, devices, and bot filters.
> 3. Verify assignment telemetry triggers (ensuring assignment fires *at* rendering rather than after downstream interactions).
> 4. Fix the ingestion bug and relaunch the experiment with fresh cohorts."

---

### Question 2: Why did you model your Power BI consumption layer as a Kimball Star Schema rather than One Big Table (OBT)?

**Model Answer:**
> "While One Big Table (OBT) works well for ad-hoc SQL queries in serverless cloud warehouses like BigQuery or Snowflake, Microsoft Power BI's in-memory **VertiPaq columnar engine** is architected specifically to maximize performance on **Star Schemas**.
>
> We implemented a Star Schema with 4 fact tables (`fct_funnel`, `fct_orders`, `fct_user_retention`, `fct_ab_test`) connected to 3 conformed dimension tables (`dim_users`, `dim_products`, `dim_date`) via 1-to-many, single-direction relationships for three specific architectural reasons:
>
> 1. **VertiPaq Compression & Memory Footprint:**
>    VertiPaq builds dictionary encoding per column. In an OBT model with 100,000 sessions, repeating string columns like `customer_segment`, `country`, and `acquisition_channel` across millions of joined rows destroys dictionary compression and inflates memory usage by 4x to 8x. In a Star Schema, strings exist only in the dimension tables, while fact tables store dense, highly compressible integer foreign keys.
>
> 2. **DAX Simplicity & Filter Context Ambiguity:**
>    Writing DAX against OBT requires complex `CALCULATE(..., ALLEXCEPT(...))` filters to avoid double-counting user attributes across multi-line order transactions. In a Star Schema, dimension slicers naturally propagate downstream to all 4 fact tables through relational filter context without requiring defensive DAX measures.
>
> 3. **Role-Playing Dimensions & Granularity Mismatches:**
>    `fct_funnel` is session-grained (100K rows), `fct_orders` is transaction-grained (10K rows), and `fct_user_retention` is monthly user-grained. Forcing these into OBT creates massive sparsity, null proliferation, and Cartesian expansion. The Star Schema cleanly preserves true table granularities."

---

### Question 3: How do you implement idempotent, cost-effective incremental models in dbt on Google BigQuery?

**Model Answer:**
> "In high-volume e-commerce event pipelines, rebuilding entire fact tables daily is cost-prohibitive and creates database locks. We implement an **incremental merge materialization** with a **3-day lookback window** in dbt.
>
> In our dbt configuration for `fct_funnel`:
> ```sql
> {{
>   config(
>     materialized = 'incremental',
>     unique_key = 'session_id',
>     on_schema_change = 'sync_all_columns',
>     partition_by = {'field': 'session_date', 'data_type': 'date', 'granularity': 'day'},
>     cluster_by = ['device_type', 'country', 'traffic_source', 'ab_variant']
>   )
> }}
>
> WITH sessions AS (
>     SELECT * FROM {{ ref('stg_sessions') }}
>     {% if is_incremental() %}
>       WHERE session_start >= (
>           SELECT TIMESTAMP_SUB(MAX(session_start), INTERVAL 3 DAY) FROM {{ this }}
>       )
>     {% endif %}
> )
> ```
>
> **Key Engineering Details:**
> 1. **Idempotency via `MERGE`:** Specifying `unique_key = 'session_id'` instructs dbt to execute an atomic `MERGE INTO` statement in BigQuery. If a session already exists (e.g., reprocessed in a backfill), it updates existing values; if new, it inserts. Re-running the pipeline 10 times produces the exact same state without duplicate rows.
> 2. **Partition Pruning:** The lookback filter `WHERE session_start >= TIMESTAMP_SUB(...)` ensures BigQuery scans only the last 3 partitions (72 hours) rather than the entire historical dataset, reducing scanned bytes and cloud compute costs by over 90%.
> 3. **Late-Arriving Fact Handling:** The 3-day lookback window provides resilience against delayed offline conversions, attribution updates, and asynchronous payment gateway confirmations."

---

### Question 4: How do you design an automated data quality circuit breaker in an orchestration DAG to protect executive reporting?

**Model Answer:**
> "A data quality circuit breaker prevents bad, incomplete, or corrupted data from propagating to executive dashboards. Silent data corruption is worse than pipeline downtime because executives make costly business decisions based on erroneous KPIs.
>
> In PulseCart, we designed a fail-fast circuit breaker pattern orchestrated through Apache Airflow:
>
> ```
> Ingestion Sensor -> Staging Views -> Intermediate Models -> [CIRCUIT BREAKER: dbt Tests] -> Marts -> [CIRCUIT BREAKER: Mart Tests] -> Power BI Refresh
> ```
>
> **Circuit Breaker Mechanics:**
> 1. **Pre-Marts Validation Gate:** Before materializing consumption marts, dbt runs generic schema tests (`unique`, `not_null`, `relationships`) on intermediate aggregations.
> 2. **Hard-Halt Execution:** If any primary key has duplicates, any foreign key fails referential integrity, or monetary totals violate reconciliation constraints (`abs(total_amount - calculated_total) > $0.01`), the task immediately exits with code 1.
> 3. **Suspension of Downstream Refresh:** Airflow DAG dependencies prevent the `trigger_powerbi_dataset_refresh` operator from executing. Power BI retains the previous day's clean data rather than displaying corrupted or null metrics.
> 4. **Automated Incident Triage:** Airflow's `on_failure_callback` fires a P1 incident webhook to `#data-ops-alerts` containing the exact model name, failed SQL assertion, and query trace."

---

### Question 5: How do you handle non-normal, heavily skewed data (such as Revenue per User) in experimentation versus binary conversion rates?

**Model Answer:**
> "In PulseCart, our primary experiment evaluated **Checkout Conversion Rate**, which is a Bernoulli random variable where individual session outcomes are binary (0 or 1). Because sample sizes were large ($N > 8,000$ per variant), the Central Limit Theorem guarantees that the sample proportion distribution is asymptotically normal, allowing us to use a standard **Two-Proportion Z-Test**:
>
> $$Z = \frac{\hat{p}_t - \hat{p}_c}{\sqrt{\hat{p}_{\text{pool}}(1 - \hat{p}_{\text{pool}})(\frac{1}{N_c} + \frac{1}{N_t})}}$$
>
> However, when analyzing **Revenue per User (ARPU)** or **Customer Lifetime Value (LTV)**, the distribution is highly non-normal:
> - It has an extreme point mass at zero (the 90% of visitors who do not buy).
> - For purchasing visitors, order values follow a right-skewed, heavy-tailed distribution (Pareto or Log-Normal).
>
> **Methodologies for Evaluating Revenue Metrics:**
> 1. **Two-Part Hurdle Model:** Decompose ARPU into two separate statistical models:
>    $$\mathbb{E}[\text{Revenue}] = P(\text{Conversion} > 0) \times \mathbb{E}[\text{Order Value} \mid \text{Conversion} > 0]$$
>    Test conversion with a Two-Proportion Z-Test, and test conditional AOV among converters using Welch's t-test or Mann-Whitney U.
> 2. **Non-Parametric Bootstrap:** Resample the control and treatment revenue distributions with replacement (10,000 iterations) to compute empirical confidence intervals for mean revenue difference without making parametric normality assumptions.
> 3. **CUPED (Controlled-experiment Using Pre-Experiment Data):** Utilize pre-experiment user spend as a covariate to reduce variance in post-experiment revenue metrics, shrinking required sample size and accelerating experiment velocity by 30–50%."

---

### Question 6: Why restructure an analytics & experimentation pipeline with Kedro and dbt together? Explain how Nodes, the Data Catalog, Pipeline Registry, and Parameters function in production.

**Model Answer:**
> "In enterprise data environments, bridging the gap between data warehouse ELT and scientific Python experimentation is one of the hardest architectural challenges. Restructuring PulseCart as a **Kedro + dbt hybrid pipeline** provides the optimal separation of concerns:
>
> 1. **Why dbt + Kedro Together (The Synergistic Architecture):**
>    - **dbt's Domain:** In-warehouse transformations where SQL pushdown is fastest and cheapest (BigQuery/Snowflake compute). dbt excels at staging views, dimensional joins, surrogate key generation, and relational schema tests.
>    - **Kedro's Domain:** Modular software engineering for scientific Python workflows. dbt cannot natively run parametric statistical hypothesis tests (`scipy.stats` for two-proportion z-tests, SRM $\chi^2$ goodness-of-fit, Delta Method confidence intervals, or non-linear cohort retention curves).
>    - **The Synergy:** Kedro wraps the dbt execution into upstream DAG nodes (`dbt_pipeline`), ensuring marts are materialized and verified by 115+ schema tests before downstream Python analytics nodes (`analytics_pipeline`) ingest the tables directly via the Kedro Data Catalog.
>
> 2. **Kedro Core Concepts Explained:**
>    - **Nodes (`nodes.py`):**
>      A Node is a pure, stateless Python function with explicitly declared inputs and outputs. Nodes have zero awareness of file paths, SQL connection drivers, or cloud buckets — they simply accept in-memory objects (like `pd.DataFrame`) and return transformed outputs. This makes unit testing trivial and eliminates side-effect bugs.
>    - **Data Catalog (`catalog.yml`):**
>      The Data Catalog is Kedro's declarative abstraction layer between computation and storage. Instead of hardcoding `pd.read_parquet('data/marts/fct_ab_test.parquet')` inside analytical code, we declare `fct_ab_test` in YAML. In local development, it points to Parquet files; in cloud production, we change the catalog type to `kedro_datasets.pandas.GBQTableDataset` pointing to BigQuery without modifying a single line of node Python logic.
>    - **Pipeline Registry (`pipeline_registry.py`):**
>      The registry discovers and organizes composite `Pipeline` objects. Nodes declare data dependencies, and Kedro automatically computes the topological execution graph (DAG). In PulseCart, the registry exposes modular sub-pipelines:
>      - `kedro run --pipeline dbt_pipeline`: Executes only the warehouse ELT and data quality checks.
>      - `kedro run --pipeline analytics_pipeline`: Executes only the statistical engines on existing marts.
>      - `kedro run`: Executes the end-to-end `__default__` pipeline.
>    - **Parameters (`parameters*.yml`):**
>      Centralizes all business logic thresholds ($\alpha = 0.05$, $95\%$ confidence intervals, SRM threshold $\alpha = 0.01$, cohort window horizons). Parameters are injected into node signatures automatically, preventing magic numbers from polluting Python logic.
>    - **Hooks & Observability (`settings.py`):**
>      Lifecycle event interceptors (`before_node_run`, `after_node_run`, `on_pipeline_error`). In PulseCart, hooks act as automated circuit breakers: if a data quality test fails, the hook immediately halts the session and aborts downstream Power BI REST API refreshes to prevent corrupt metrics from reaching executive dashboards."
