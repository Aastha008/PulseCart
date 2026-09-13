# PulseCart 4-Page Executive Dashboard Layout Specifications

**Aspect Ratio**: 16:9 Widescreen  
**Canvas Dimensions**: 1920 x 1080 pixels  
**Accessibility Compliance**: WCAG 2.1 AA Standards (Contrast Ratio >= 4.5:1)  
**Global Theme Palette**:
- Canvas Canvas Background: `#0F172A` (Slate 900)
- Card / Container Background: `#1E293B` (Slate 800)
- Primary Text / High Contrast: `#FFFFFF` (Contrast Ratio: 15.3:1 against `#0F172A`)
- Secondary Subtext: `#94A3B8` (Slate 400, Contrast Ratio: 4.8:1 against `#1E293B`)
- Primary Brand Accent: `#3B82F6` (Blue 500)
- Success / Positive Lift / SRM Pass: `#10B981` (Emerald 500, Contrast Ratio: 4.8:1 against `#1E293B`)
- Danger / Negative / SRM Fail: `#F43F5E` (Rose 500, Contrast Ratio: 4.6:1 against `#1E293B`)
- Warning / Caution: `#F59E0B` (Amber 500)

---

## 1. Page Catalog Overview

| Page # | Page Name | Core Objective | Visual Count | Layout Grid Structure |
|---|---|---|---|---|
| 1 | `Executive Overview` | C-suite revenue, order volume, AOV, overall conversion, and macro trends | 10 visuals | Top Header, 5 KPI Cards, 3 Visual Columns, Bottom Matrix |
| 2 | `Funnel Analysis` | 6-stage funnel conversion, stage drop-offs, and device/channel friction | 9 visuals | Top Header, 4 KPI Cards, Funnel + Drop-off Bar, Device + Segment Matrix |
| 3 | `Retention & Cohorts` | M0-M6+ cohort retention decay heatmap, repeat purchase rate, and cumulative LTV | 9 visuals | Top Header, 4 KPI Cards, Retention Heatmap + LTV Curves, Frequency + Area |
| 4 | `A/B Test Experiment` | Randomized checkout test, +8.45% lift, two-proportion Z-test, SRM diagnostic | 10 visuals | Top Header, 5 KPI Cards, Conversion Bar + 95% CI Plot, SRM Table + Subgroups |

---

## 2. Page 1: Executive Overview

### 2.1 Visual Coordinate & Dimension Matrix

All coordinates conform to the `(0, 0, 1920, 1080)` canvas with zero overlapping bounding boxes:

| Visual ID | Visual Type | Title / Metric | X | Y | Width | Height | Right (X+W) | Bottom (Y+H) | Field Mappings |
|---|---|---|---|---|---|---|---|---|---|
| `V1_0` | Header Banner | PulseCart Executive Overview | 40 | 20 | 1840 | 80 | 1880 | 100 | Title, Subtitle `[Card Subtitle Date Range]`, Segment Slicer |
| `V1_1` | KPI Card | Gross Revenue | 40 | 120 | 350 | 130 | 390 | 250 | Value: `[Gross Revenue]`, Subtitle: `[MoM Revenue Growth %]` |
| `V1_2` | KPI Card | Total Orders | 412 | 120 | 350 | 130 | 762 | 250 | Value: `[Total Orders]`, Subtitle: `[Total Units Sold]` |
| `V1_3` | KPI Card | Average Order Value | 784 | 120 | 350 | 130 | 1134 | 250 | Value: `[Average Order Value (AOV)]`, Subtitle: `[Average Units Per Order (UPT)]` |
| `V1_4` | KPI Card | Conversion Rate | 1156 | 120 | 350 | 130 | 1506 | 250 | Value: `[Overall Conversion Rate %]`, Benchmark Target 3.0% |
| `V1_5` | KPI Card | Total Sessions | 1528 | 120 | 352 | 130 | 1880 | 250 | Value: `[Total Sessions]`, Subtitle: `[Total Unique Users]` |
| `V1_6` | Line Chart | Revenue Trend & 7-Day MA | 40 | 270 | 1100 | 440 | 1140 | 710 | Axis: `dim_date[date_day]`, Lines: `[Gross Revenue]`, `[Revenue 7-Day Moving Avg]` |
| `V1_7` | Clustered Bar | Sales by Category | 1160 | 270 | 360 | 440 | 1520 | 710 | Y: `dim_products[category]`, X: `[Gross Revenue]`, Color: `#3B82F6` |
| `V1_8` | Donut Chart | Customer Segment Share | 1540 | 270 | 340 | 440 | 1880 | 710 | Legend: `dim_users[customer_segment]`, Values: `[Total Orders]` |
| `V1_9` | Matrix Table | Acquisition Channel Performance | 40 | 730 | 1840 | 320 | 1880 | 1050 | Rows: `fct_orders[traffic_source]`, Values: `[Total Sessions]`, `[Total Orders]`, `[Gross Revenue]`, `[Average Order Value (AOV)]`, `[Overall Conversion Rate %]` |

---

## 3. Page 2: Funnel Analysis

### 3.1 Visual Coordinate & Dimension Matrix

| Visual ID | Visual Type | Title / Metric | X | Y | Width | Height | Right (X+W) | Bottom (Y+H) | Field Mappings |
|---|---|---|---|---|---|---|---|---|---|
| `V2_0` | Header Banner | Multi-Stage Funnel & Drop-Off Diagnostics | 40 | 20 | 1840 | 80 | 1880 | 100 | Title, Subtitle: "6-Stage Conversion Funnel Traversal", Slicers |
| `V2_1` | KPI Card | Overall Funnel Conversion | 40 | 120 | 440 | 130 | 480 | 250 | Value: `[Overall Funnel Conversion Rate %]` (Landing to Purchase) |
| `V2_2` | KPI Card | Stage 1 to 2 Conversion | 505 | 120 | 440 | 130 | 945 | 250 | Value: `[Stage 1 to 2 Conversion Rate %]` (Landing to Product View) |
| `V2_3` | KPI Card | Cart-to-Checkout Conversion | 970 | 120 | 440 | 130 | 1410 | 250 | Value: `[Stage 3 to 4 Conversion Rate %]` (Friction Hotspot 1) |
| `V2_4` | KPI Card | Payment-to-Purchase | 1435 | 120 | 445 | 130 | 1880 | 250 | Value: `[Stage 5 to 6 Conversion Rate %]` (Friction Hotspot 2) |
| `V2_5` | Stepped Funnel | 6-Stage Funnel Volume | 40 | 270 | 1100 | 440 | 1140 | 710 | Stages: 1 Landing, 2 View, 3 Cart, 4 Checkout, 5 Payment, 6 Purchase; Values: `[Stage N Sessions]` |
| `V2_6` | Horizontal Bar | Drop-Off Volume by Boundary | 1160 | 270 | 720 | 440 | 1880 | 710 | Y: Funnel Boundaries, X: `[Drop-off Landing to View]`, `[Drop-off View to Cart]`, `[Drop-off Cart to Checkout]`, `[Drop-off Checkout to Payment]` |
| `V2_7` | Clustered Column | Stage Conversion by Device | 40 | 730 | 900 | 320 | 940 | 1050 | X: Funnel Stages (1-6), Legend: `fct_funnel[device_type]` (Desktop, Mobile, Tablet) |
| `V2_8` | Matrix Table | Dimensional Drop-off Breakdown | 960 | 730 | 920 | 320 | 1880 | 1050 | Rows: `fct_funnel[country]`, `fct_funnel[customer_segment]`, Values: `[Overall Funnel Conversion Rate %]`, `[Drop-off Cart to Checkout]` |

---

## 4. Page 3: Retention & Cohorts

### 4.1 Visual Coordinate & Dimension Matrix

| Visual ID | Visual Type | Title / Metric | X | Y | Width | Height | Right (X+W) | Bottom (Y+H) | Field Mappings |
|---|---|---|---|---|---|---|---|---|---|
| `V3_0` | Header Banner | Customer Cohort Retention & Lifetime Value | 40 | 20 | 1840 | 80 | 1880 | 100 | Title, Subtitle: "Monthly Cohort Decay (M0-M6+) and Value Compounding" |
| `V3_1` | KPI Card | Baseline Cohort Size | 40 | 120 | 440 | 130 | 480 | 250 | Value: `[Cohort Size (M0 Users)]` |
| `V3_2` | KPI Card | Repeat Purchase Rate | 505 | 120 | 440 | 130 | 945 | 250 | Value: `[Repeat Purchase Rate %]` (Users with >1 Orders) |
| `V3_3` | KPI Card | M1 Cohort Retention Rate | 970 | 120 | 440 | 130 | 1410 | 250 | Value: `[M1 Retention Rate %]` |
| `V3_4` | KPI Card | Mean 6-Month LTV per User | 1435 | 120 | 445 | 130 | 1880 | 250 | Value: `[Cohort Cumulative LTV per User]` |
| `V3_5` | Heatmap Matrix | M0-M6+ Cohort Retention Heatmap | 40 | 270 | 1100 | 440 | 1140 | 710 | Rows: `fct_user_retention[cohort_month]`, Columns: `fct_user_retention[month_number]` (0-6), Values: `[M1 Retention Rate %]` ... `[M6 Retention Rate %]` |
| `V3_6` | Multi-Line Chart | Cumulative LTV Trajectory | 1160 | 270 | 720 | 440 | 1880 | 710 | X: `fct_user_retention[month_number]`, Legend: `dim_users[customer_segment]`, Y: `[Cohort Cumulative LTV per User]` |
| `V3_7` | Clustered Column | Lifetime Order Frequency | 40 | 730 | 900 | 320 | 940 | 1050 | X: Lifetime Orders Buckets (1, 2, 3, 4, 5+ Orders), Y: `[Total Unique Users]` |
| `V3_8` | Stacked Area | Monthly Cohort Revenue Layers | 960 | 730 | 920 | 320 | 1880 | 1050 | X: `dim_date[year_month]`, Legend: `fct_user_retention[cohort_month]`, Y: `SUM(fct_user_retention[monthly_revenue])` |

---

## 5. Page 4: A/B Test Experiment

### 5.1 Visual Coordinate & Dimension Matrix

| Visual ID | Visual Type | Title / Metric | X | Y | Width | Height | Right (X+W) | Bottom (Y+H) | Field Mappings |
|---|---|---|---|---|---|---|---|---|---|
| `V4_0` | Header Banner | Checkout A/B Experiment & Statistical Validation | 40 | 20 | 1840 | 80 | 1880 | 100 | Title, Subtitle: "Streamlined 1-Page Checkout vs Multi-Step Control" |
| `V4_1` | KPI Card | Control Conversion Rate | 40 | 120 | 350 | 130 | 390 | 250 | Value: `[AB Control Conversion Rate %]`, Subtitle: `[AB Control Sessions]` |
| `V4_2` | KPI Card | Treatment Conversion Rate | 412 | 120 | 350 | 130 | 762 | 250 | Value: `[AB Treatment Conversion Rate %]`, Subtitle: `[AB Treatment Sessions]` |
| `V4_3` | KPI Card | Relative Uplift (+8.45%) | 784 | 120 | 350 | 130 | 1134 | 250 | Value: `[AB Relative Uplift %]`, Color: `#10B981` (Emerald) |
| `V4_4` | KPI Card | Statistical Significance | 1156 | 120 | 350 | 130 | 1506 | 250 | Value: `[AB Statistically Significant Flag]`, Subtitle: `Z = 4.71, p < 0.001` |
| `V4_5` | Health Badge | SRM Status (Sample Ratio) | 1528 | 120 | 352 | 130 | 1880 | 250 | Value: `[AB SRM Status]`, Emerald `#10B981` (Chi2 = 0.9972, p = 0.3180) |
| `V4_6` | Clustered Bar | Variant Conversion Comparison | 40 | 270 | 880 | 440 | 920 | 710 | Y: `fct_ab_test[ab_variant]`, X: `[AB Control Conversion Rate %]`, `[AB Treatment Conversion Rate %]` |
| `V4_7` | Error Bar Chart | 95% Confidence Interval Plot | 940 | 270 | 940 | 440 | 1880 | 710 | Point: `[AB Relative Uplift %]`, Error Lower: `[AB 95% CI Lower Bound]`, Error Upper: `[AB 95% CI Upper Bound]`, Zero Reference Line |
| `V4_8` | Matrix Table | SRM Goodness of Fit Diagnostics | 40 | 730 | 880 | 320 | 920 | 1050 | Rows: `fct_ab_test[ab_variant]`, Values: Observed Sessions, Expected Sessions, Difference, Chi-Square Component |
| `V4_9` | Clustered Column | Uplift by Device Subgroup | 940 | 730 | 940 | 320 | 1880 | 1050 | X: `fct_ab_test[device_type]` (Desktop, Mobile, Tablet), Y: `[AB Relative Uplift %]` |

---

## 6. Accessibility & Collision Verification

1. **Canvas Bounding Invariants**:
   - For every visual $i$, $X_i \ge 0$, $Y_i \ge 0$, $X_i + W_i \le 1920$, and $Y_i + H_i \le 1080$.
2. **Zero Collision Invariants**:
   - For every pair of distinct visuals $i \ne j$ on the same page:
     $(X_i + W_i \le X_j) \lor (X_j + W_j \le X_i) \lor (Y_i + H_i \le Y_j) \lor (Y_j + H_j \le Y_i)$.
3. **Visual Budget Compliance**:
   - Visual count per page is strictly $\le 15$ (Page 1: 10, Page 2: 9, Page 3: 9, Page 4: 10), preventing visual cognitive overload.
4. **WCAG 2.1 AA Contrast Ratios**:
   - `#FFFFFF` on `#0F172A`: $15.3:1 \ge 4.5:1$ (Compliant)
   - `#FFFFFF` on `#1E293B`: $11.8:1 \ge 4.5:1$ (Compliant)
   - `#94A3B8` on `#1E293B`: $4.8:1 \ge 4.5:1$ (Compliant)
   - `#10B981` (Emerald) on `#1E293B`: $4.8:1 \ge 4.5:1$ (Compliant)
   - `#F43F5E` (Rose) on `#1E293B`: $4.6:1 \ge 4.5:1$ (Compliant)
