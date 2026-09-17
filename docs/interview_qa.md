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

---

### Question 7: How do you architect a multi-warehouse dbt pipeline (BigQuery + Snowflake + DuckDB) with zero SQL duplication? Explain dialect differences, macro abstraction, and partitioning vs. clustering.

**Model Answer:**
> "Supporting multiple cloud data warehouses (e.g., BigQuery, Snowflake, and local DuckDB) without duplicating SQL models is a hallmark of senior analytics engineering. Maintaining separate SQL files per warehouse creates technical debt, drift, and quadruples testing overhead.
>
> In PulseCart, we achieved **100% cross-warehouse execution across 18 models and 174 tests** using a three-tiered abstraction strategy:
>
> 1. **Cross-Warehouse Macro Abstraction (`macros/cross_warehouse.sql`):**
>    We identified dialect divergences across SQL engines and created target-aware Jinja macros:
>    - **Timestamp Differences:** BigQuery syntax is `TIMESTAMP_DIFF(end, start, unit)`, whereas Snowflake is `DATEDIFF(unit, start, end)`. Our `datediff_cross(start, end, unit)` macro inspects `target.type` at compile time and emits the appropriate dialect syntax.
>    - **Date Truncation:** BigQuery uses `DATE_TRUNC(col, MONTH)`, while Snowflake requires `DATE_TRUNC('MONTH', col)`. Abstraction: `date_trunc_cross(expr, unit)`.
>    - **Safe Division:** BigQuery provides `SAFE_DIVIDE(a, b)` which is non-standard. Snowflake lacks `SAFE_DIVIDE`. Rather than vendor-specific UDFs, our `safe_divide_cross(num, denom)` macro compiles into ANSI standard `CASE WHEN (denom) = 0 OR (denom) IS NULL THEN NULL ELSE (num) / (denom) END`, which executes identically across BigQuery, Snowflake, DuckDB, and Postgres with zero runtime overhead.
>    - **Logical Aggregations:** BigQuery supports `LOGICAL_OR(condition)`. Snowflake does not. We rewrote this using ANSI SQL: `MAX(CASE WHEN condition THEN 1 ELSE 0 END) = 1`, which natively evaluates to a boolean across all warehouses.
>
> 2. **Config-Aware Partitioning & Clustering:**
>    - BigQuery requires a `partition_by` dictionary (`{'field': 'date_col', 'data_type': 'date', 'granularity': 'day'}`). In Snowflake, partition dictionaries cause a hard compilation error because Snowflake automatically manages micro-partitioning (50–500 MB columnar blocks).
>    - In PulseCart, we parameterized the dbt model configurations dynamically:
>      ```sql
>      partition_by = {
>        'field': 'session_date', 'data_type': 'date', 'granularity': 'day'
>      } if target.type == 'bigquery' else none,
>      cluster_by = ['device_type', 'country', 'traffic_source', 'ab_variant']
>      ```
>      This gives BigQuery explicit daily partitioning while allowing Snowflake to leverage the clustering keys to optimize micro-partition pruning.
>
> 3. **Synthetic Spine Generation (`dim_date`):**
>    - BigQuery generates date spines via `UNNEST(GENERATE_DATE_ARRAY(...))`.
>    - Snowflake achieves this via `TABLE(GENERATOR(ROWCOUNT => 1096))` joined with `SEQ4()`.
>    - Our `dim_date.sql` utilizes target branching to generate 3 full calendar years of dates natively on each platform."

---

### Question 8: What problem do Snowflake Streams & Tasks solve over traditional high-watermark dbt incremental models? Explain Change Data Capture (CDC) mechanics and compute optimization.

**Model Answer:**
> "In high-velocity clickstream event pipelines (like PulseCart's 230K+ events), traditional dbt incremental materialization uses high-watermark filtering:
> `WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})`
>
> While simple, this approach has three critical architectural flaws:
> 1. **Late-Arriving Fact Loss:** Mobile devices caching events offline or asynchronous payment webhooks often arrive with timestamps hours or days older than the current high-watermark. High-watermark queries permanently miss these events unless costly lookback windows are applied.
> 2. **No CDC (Deletes & Updates):** High-watermark filtering only detects new rows. Source updates (e.g. order status changes from 'pending' to 'cancelled') or hard deletes are invisible.
> 3. **Compute Waste:** Scanning high-volume raw tables every 5–15 minutes on a scheduled warehouse wakes up virtual compute and consumes credits even when zero new events have landed.
>
> **The Snowflake Streams & Tasks Solution:**
> In PulseCart Stage 4, we implemented native Change Data Capture (CDC):
> - **Snowflake Stream (`STREAM_RAW_EVENTS`):** An append-only stream placed on `RAW_PULSECART.RAW_EVENTS`. The stream creates an offset pointer into Snowflake's immutable micro-partition version log without copying data. It tracks row delta and provides metadata columns: `METADATA$ACTION` ('INSERT'), `METADATA$ISUPDATE`, and `METADATA$ROW_ID`.
> - **Snowflake Task (`TSK_INGEST_STG_EVENTS`):** A scheduled task executing a `MERGE INTO STAGING.STG_EVENTS_CDC` query. Crucially, the task includes the guard condition:
>   `WHEN SYSTEM$STREAM_HAS_DATA('RAW_PULSECART.STREAM_RAW_EVENTS')`
>
> **Compute Optimization (Zero Idle Cost):**
> Snowflake evaluates `SYSTEM$STREAM_HAS_DATA()` at the cloud services metadata layer in sub-seconds without spinning up the virtual warehouse. If no new events arrived, the warehouse remains suspended and consumes **zero credits**. When data arrives, the task wakes the warehouse, merges only the delta records into staging, and atomically advances the stream offset upon commit."

---

### Question 9: How do you design and execute a sub-second disaster recovery strategy using Snowflake Time Travel following a corrupted batch ETL run?

**Model Answer:**
> "Data corruption in production marts is an inevitable operational reality — whether caused by a malformed incremental merge, an accidental unconstrained `UPDATE`, or an errant administrative `DROP TABLE`. In traditional warehouses or legacy RDBMS, recovering from such an incident requires restoring multi-terabyte backups, spinning up staging servers, and replaying raw logs, incurring hours or days of Recovery Time Objective (RTO).
>
> In PulseCart Stage 5, we simulated and verified a mission-critical disaster recovery scenario on `MARTS.FCT_ORDERS` (10,022 orders, $2,101,303.00 revenue):
>
> 1. **The Incident:**
>    A buggy batch script executed an unconstrained update:
>    `UPDATE MARTS.FCT_ORDERS SET total_amount = 0.0, subtotal = 0.0 WHERE order_date >= '2025-01-01';`
>    Downstream Power BI dashboards showed $0.00 revenue, triggering a P1 data outage.
>
> 2. **Snowflake Micro-Partition Immobility:**
>    Snowflake micro-partitions are immutable. When an `UPDATE` executes, Snowflake does not overwrite existing data in place; it marks the old micro-partitions as inactive and writes new micro-partitions containing the zeroes. The old micro-partitions remain accessible via Time Travel for up to 90 days.
>
> 3. **Forensics via Query History:**
>    We captured the offending statement ID directly from cursor metadata or `INFORMATION_SCHEMA.QUERY_HISTORY()`:
>    `SET bad_query_id = '01c7207a-000d-ff91-0000-00023712f185';`
>
> 4. **Pre-Recovery Inspection:**
>    Before altering anything, we queried the historical state immediately prior to the corrupting query:
>    ```sql
>    SELECT COUNT(*), ROUND(SUM(total_amount), 2)
>    FROM MARTS.FCT_ORDERS BEFORE(STATEMENT => $bad_query_id);
>    ```
>    This proved the pre-incident state was completely intact ($2,101,303.00 revenue).
>
> 5. **Sub-Second Restoration:**
>    We restored the table instantaneously using statement-level Time Travel:
>    ```sql
>    CREATE OR REPLACE TABLE MARTS.FCT_ORDERS AS 
>    SELECT * FROM MARTS.FCT_ORDERS BEFORE(STATEMENT => $bad_query_id);
>    ```
>    Alternatively, we can execute a zero-copy clone:
>    `CREATE TABLE MARTS.FCT_ORDERS_RECOVERED CLONE MARTS.FCT_ORDERS BEFORE(STATEMENT => $bad_query_id);`
>
> 6. **Results & Business Impact:**
>    The entire recovery executed in **0.63 seconds** (sub-second RTO) with 100% data fidelity restored down to the exact penny, completely eliminating pipeline downtime."
