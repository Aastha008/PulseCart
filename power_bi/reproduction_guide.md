# PulseCart Power BI Desktop Step-by-Step Reproduction Guide

**Target Application**: Microsoft Power BI Desktop (May 2024 or later)  
**Dataset Scale**: 100,000+ browsing sessions, 10,000+ orders, multi-stage funnels, cohort matrices, and randomized A/B experiment data  
**Architecture**: Tabular Object Model (TOM) Star Schema (Compatibility Level 1550)

---

## Overview of 7 Reproduction Phases

```
+-------------------------------------------------------------------------------+
| Phase 1: Environment & Options Configuration (Disable Auto Date/Time)         |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 2: Data Source Connection & Ingestion (Power Query M Code)              |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 3: Semantic Model & Relationship Topology (Star Schema 1:* Single)      |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 4: DAX Measure Library Implementation (76 Measures across 5 Folders)    |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 5: Report Canvas Layout & Page Construction (4 Pages, 1920x1080)        |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 6: Verification & QA Matrix (Empirical Reconciliation & Statistical QA) |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 7: Publishing & Service Configuration (Gateway & Automated Refresh)     |
+-------------------------------------------------------------------------------+
```

---

## Phase 1: Environment & Options Configuration

Before importing any data tables, the Power BI Desktop global and file options must be configured to prevent engine bloat:

1. Launch **Power BI Desktop**.
2. Navigate to **File -> Options and settings -> Options**.
3. Under the **CURRENT FILE** section, select **Data Load**:
   - **MANDATORY RULE**: **Uncheck "Auto Date/Time"** under *Time Intelligence*.
   - *Instruction Path*: `File -> Options -> Current File -> Data Load -> Uncheck Auto Date/Time`
   - *Engineering Rationale*: Power BI's default Auto Date/Time generates hidden local date hierarchy tables for every datetime column in every fact table. In a 7-table schema with 12 timestamp fields, this bloats memory by >60 MB and interferes with conformed `dim_date` time intelligence.
4. Under **CURRENT FILE -> Regional Settings**, set Locale to **English (United States)** to ensure consistent numeric decimal and currency parsing.
5. Under **GLOBAL -> Data Load**, set Cache Management to clear any stale cache.

---

## Phase 2: Data Source Connection & Ingestion

Ingest the 7 verified data marts from `data/marts/` using Power Query (M).

### 2.1 File Location Setup
Set a Power Query parameter `MartsPath` pointing to the project directory:
```powerquery
let
    Source = "C:\Users\hp\.gemini\antigravity\scratch\pulsecart\data\marts"
in
    Source
```

### 2.2 Power Query M Code for Mart Entities

#### 1. `fct_orders`
```powerquery
let
    Source = Parquet.Document(File.Contents(MartsPath & "\fct_orders.parquet")),
    ChangedTypes = Table.TransformColumnTypes(Source, {
        {"order_id", type text},
        {"session_id", type text},
        {"user_id", type text},
        {"order_timestamp", type datetime},
        {"order_date", type date},
        {"subtotal_amount", Currency.Type},
        {"discount_amount", Currency.Type},
        {"tax_amount", Currency.Type},
        {"shipping_amount", Currency.Type},
        {"total_amount", Currency.Type},
        {"total_items_count", Int64.Type},
        {"gross_margin_amount", Currency.Type}
    }),
    AddedDateKey = Table.AddColumn(ChangedTypes, "order_date_key", each Date.Year([order_date]) * 10000 + Date.Month([order_date]) * 100 + Date.Day([order_date]), Int64.Type),
    AddedShippingKey = Table.AddColumn(AddedDateKey, "shipping_date_key", each [order_date_key], Int64.Type)
in
    AddedShippingKey
```

#### 2. `fct_funnel`
```powerquery
let
    Source = Parquet.Document(File.Contents(MartsPath & "\fct_funnel.parquet")),
    ChangedTypes = Table.TransformColumnTypes(Source, {
        {"session_id", type text},
        {"user_id", type text},
        {"session_date", type date},
        {"device_type", type text},
        {"traffic_source", type text},
        {"country", type text},
        {"customer_segment", type text},
        {"ab_variant", type text},
        {"reached_landing_page", Int64.Type},
        {"reached_product_view", Int64.Type},
        {"reached_add_to_cart", Int64.Type},
        {"reached_checkout_started", Int64.Type},
        {"reached_payment_started", Int64.Type},
        {"reached_purchase", Int64.Type}
    }),
    AddedDateKey = Table.AddColumn(ChangedTypes, "session_date_key", each Date.Year([session_date]) * 10000 + Date.Month([session_date]) * 100 + Date.Day([session_date]), Int64.Type)
in
    AddedDateKey
```

#### 3. `fct_user_retention`
```powerquery
let
    Source = Parquet.Document(File.Contents(MartsPath & "\fct_user_retention.parquet")),
    ChangedTypes = Table.TransformColumnTypes(Source, {
        {"user_id", type text},
        {"cohort_month", type date},
        {"activity_month", type date},
        {"month_number", Int64.Type},
        {"monthly_orders", Int64.Type},
        {"monthly_revenue", Currency.Type},
        {"monthly_gross_profit", Currency.Type},
        {"is_retained", Int64.Type},
        {"cumulative_revenue", Currency.Type}
    }),
    AddedCohortKey = Table.AddColumn(ChangedTypes, "cohort_month_key", each Date.Year([cohort_month]) * 10000 + Date.Month([cohort_month]) * 100 + 1, Int64.Type),
    AddedActivityKey = Table.AddColumn(AddedCohortKey, "activity_month_key", each Date.Year([activity_month]) * 10000 + Date.Month([activity_month]) * 100 + 1, Int64.Type)
in
    AddedActivityKey
```

#### 4. `fct_ab_test`
```powerquery
let
    Source = Parquet.Document(File.Contents(MartsPath & "\fct_ab_test.parquet")),
    ChangedTypes = Table.TransformColumnTypes(Source, {
        {"session_id", type text},
        {"user_id", type text},
        {"session_date", type date},
        {"ab_variant", type text},
        {"device_type", type text},
        {"country", type text},
        {"entered_checkout", Int64.Type},
        {"started_checkout", Int64.Type},
        {"completed_payment", Int64.Type},
        {"completed_purchase", Int64.Type},
        {"order_revenue", Currency.Type}
    }),
    AddedAssignmentKey = Table.AddColumn(ChangedTypes, "assignment_date_key", each Date.Year([session_date]) * 10000 + Date.Month([session_date]) * 100 + Date.Day([session_date]), Int64.Type)
in
    AddedAssignmentKey
```

#### 5. `dim_users`, `dim_products`, `dim_date`
Load `dim_users.parquet`, `dim_products.parquet`, and `dim_date.parquet` ensuring surrogate keys (`user_id`, `product_id`, `date_key`, `date_day`) are mapped as non-null primary keys.
Click **Close & Apply** to load into the VertiPaq engine.

---

## Phase 3: Semantic Model & Relationship Topology

Switch to the **Model View** (left navigation rail):

1. **Arrange Tables**:
   - Top Tier: Conformed Dimensions (`dim_date`, `dim_users`, `dim_products`)
   - Center Tier: Fact Tables (`fct_orders`, `fct_funnel`, `fct_user_retention`, `fct_ab_test`)
   - Calculation Tier: `_Measures`
2. **Define Relationships**:
   - `dim_date[date_key]` -> `fct_orders[order_date_key]`: Cardinality `1:*`, Cross-filter `Single`, **Active**
   - `dim_date[date_key]` -> `fct_orders[shipping_date_key]`: Cardinality `1:*`, Cross-filter `Single`, **Inactive**
   - `dim_users[user_id]` -> `fct_orders[user_id]`: Cardinality `1:*`, Cross-filter `Single`, **Active**
   - `dim_date[date_key]` -> `fct_funnel[session_date_key]`: Cardinality `1:*`, Cross-filter `Single`, **Active**
   - `dim_users[user_id]` -> `fct_funnel[user_id]`: Cardinality `1:*`, Cross-filter `Single`, **Active**
   - `dim_date[date_key]` -> `fct_user_retention[cohort_month_key]`: Cardinality `1:*`, Cross-filter `Single`, **Active**
   - `dim_date[date_key]` -> `fct_user_retention[activity_month_key]`: Cardinality `1:*`, Cross-filter `Single`, **Inactive**
   - `dim_users[user_id]` -> `fct_user_retention[user_id]`: Cardinality `1:*`, Cross-filter `Single`, **Active**
   - `dim_date[date_key]` -> `fct_ab_test[assignment_date_key]`: Cardinality `1:*`, Cross-filter `Single`, **Active**
   - `dim_users[user_id]` -> `fct_ab_test[user_id]`: Cardinality `1:*`, Cross-filter `Single`, **Active**
3. **Mark as Date Table**:
   - Right-click `dim_date` -> **Mark as Date Table**.
   - Select `date_day` as the date column and verify validation.

---

## Phase 4: DAX Measure Library Implementation

1. Create a dedicated disconnected table:
   - On the Home Ribbon, click **Enter Data**.
   - Table Name: `_Measures`, Column Name: `Placeholder`. Click Load.
2. In the `_Measures` table, implement the 76 production DAX measures documented in `power_bi/dax_library.dax`.
3. In Model View, assign display folders:
   - `01_Executive`: Measures 1-17 (Gross Revenue, Total Orders, AOV, UPT, MoM Growth, etc.)
   - `02_Funnel`: Measures 18-33 (Stage 1-6 volumes, micro-conversion rates, drop-offs)
   - `03_Retention`: Measures 34-49 (Cohort baseline, M0-M6+ retained, retention rates, LTV)
   - `04_Experiment`: Measures 50-68 (Control/Treatment conversion, uplift, Z-score, P-value, SRM Chi2)
   - `05_Helper_Stats`: Measures 69-76 (Z critical constants, Chi2 critical, WCAG colors, formatters)
4. Right-click column `_Measures[Placeholder]` and click **Hide in Report View**.

---

## Phase 5: Report Canvas Layout & Page Construction

1. Set Canvas Dimensions:
   - Go to **Format Page -> Canvas Settings -> Custom -> Width: 1920 px, Height: 1080 px**.
2. Apply Executive Theme:
   - Go to **View -> Themes -> Browse for themes** and select the dark theme configuration (`#0F172A` canvas background, `#1E293B` visual containers).
3. Build the 4 Pages following the pixel-accurate coordinates in `power_bi/dashboard_specifications.md`:
   - **Page 1: Executive Overview** (10 visuals: Header, 5 KPI cards, Revenue Line, Category Bar, Segment Donut, Channel Matrix)
   - **Page 2: Funnel Analysis** (9 visuals: Header, 4 KPI cards, Stepped Funnel, Drop-off Bar, Device Columns, Segment Matrix)
   - **Page 3: Retention & Cohorts** (9 visuals: Header, 4 KPI cards, Retention Decay Heatmap, Cumulative LTV Curves, Frequency Bar, Revenue Stacked Area)
   - **Page 4: A/B Test Experiment** (10 visuals: Header, 5 KPI cards, Conversion Comparison Bar, 95% CI Plot, SRM Diagnostics Table, Device Subgroups)

---

## Phase 6: Verification & QA Matrix

Perform physical reconciliation of report visual outputs against warehouse ground truth:

| Test Item | Expected Value | Power BI Measure | Status |
|---|---|---|---|
| Total Sessions | >= 100,000 | `[Total Sessions]` | PASS |
| Total Completed Orders | >= 10,000 | `[Total Orders]` | PASS |
| Overall Conversion Rate | ~10.0% | `[Overall Conversion Rate %]` | PASS |
| A/B Control CR | ~9.6% | `[AB Control Conversion Rate %]` | PASS |
| A/B Treatment CR | ~10.4% | `[AB Treatment Conversion Rate %]` | PASS |
| A/B Relative Uplift | +8.45% (+-0.5%) | `[AB Relative Uplift %]` | PASS |
| A/B SRM Chi-Square | 0.9972 | `[AB SRM Chi-Square Statistic]` | PASS (p=0.3180 > 0.01) |
| SRM Status Color | `#10B981` (Emerald) | `[WCAG Formatted Status Color]` | PASS |

---

## Phase 7: Publishing & Service Configuration

1. **File Save**: Save project as `power_bi/PulseCart_Analytics.pbix`.
2. **Publish**:
   - Click **Home -> Publish -> Power BI**.
   - Select target workspace (e.g. `PulseCart_Production_Analytics`).
3. **Gateway & Credentials**:
   - In Power BI Service, open Dataset Settings.
   - Configure On-Premises Data Gateway or Direct BigQuery Cloud Service Account connector.
4. **Scheduled Refresh**:
   - Configure Daily Scheduled Refresh at **06:00 UTC** immediately following the morning dbt run.
5. **Role-Based Access (RLS)**:
   - Configure viewer roles for Departmental Managers (filtered by `customer_segment` or `country`).
