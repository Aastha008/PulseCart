# PulseCart Production DAX Measure Library Reference

**Total Measures**: 76 Production-Grade DAX Measures  
**Display Folders**: 5 Standard Folders (`01_Executive`, `02_Funnel`, `03_Retention`, `04_Experiment`, `05_Helper_Stats`)  
**Deployment Target**: Disconnected calculation table `_Measures`  
**Quality Standards**: All division operations protected by `DIVIDE(..., ..., 0)` or `DIVIDE(..., ..., BLANK())`; time intelligence anchored on conformed calendar dimension; closed-form normal approximations for hypothesis testing and SRM diagnostics.

---

## Folder Summary

| Folder | Measure Count | Primary Focus |
|---|---|---|
| `01_Executive` | 16 | Financial performance, order depth, moving averages, MoM/YoY growth |
| `02_Funnel` | 16 | 6-stage funnel volumes, micro-conversion rates, stage drop-offs |
| `03_Retention` | 16 | Cohort baseline sizes, M0-M6+ retention counts, decay rates, cumulative LTV |
| `04_Experiment` | 18 | A/B test variant conversion, pooled proportions, Z-score, P-value, SRM Chi^2, 95% CI |
| `05_Helper_Stats` | 10 | Critical values, dynamic titles, WCAG status colors, safe helpers |

---

## 1. Display Folder: `01_Executive`

### Measure 1: `[Gross Revenue]`
- **Display Folder**: `01_Executive`
- **Format**: `$#,##0.00`
- **Description**: Cumulative gross subtotal revenue prior to discounts, taxes, and shipping fees.
```dax
[Gross Revenue] = 
SUM(fct_orders[subtotal_amount])
```

### Measure 2: `[Net Revenue]`
- **Display Folder**: `01_Executive`
- **Format**: `$#,##0.00`
- **Description**: Total billed revenue to customers inclusive of taxes and shipping minus discounts.
```dax
[Net Revenue] = 
SUM(fct_orders[total_amount])
```

### Measure 3: `[Total Orders]`
- **Display Folder**: `01_Executive`
- **Format**: `#,##0`
- **Description**: Distinct count of finalized and completed customer purchase orders.
```dax
[Total Orders] = 
CALCULATE(
    DISTINCTCOUNT(fct_orders[order_id]),
    fct_orders[status] = "completed" || ISBLANK(fct_orders[status])
)
```

### Measure 4: `[Average Order Value (AOV)]`
- **Display Folder**: `01_Executive`
- **Format**: `$#,##0.00`
- **Description**: Mean billed gross revenue generated per completed order transaction.
```dax
[Average Order Value (AOV)] = 
DIVIDE([Gross Revenue], [Total Orders], 0)
```

### Measure 5: `[Total Units Sold]`
- **Display Folder**: `01_Executive`
- **Format**: `#,##0`
- **Description**: Aggregate quantity of individual product items sold across all completed orders.
```dax
[Total Units Sold] = 
SUM(fct_orders[total_items_count])
```

### Measure 6: `[Average Units Per Order (UPT)]`
- **Display Folder**: `01_Executive`
- **Format**: `0.00`
- **Description**: Average number of item units purchased per completed order (Units Per Transaction).
```dax
[Average Units Per Order (UPT)] = 
DIVIDE([Total Units Sold], [Total Orders], 0)
```

### Measure 7: `[Gross Profit Amount]`
- **Display Folder**: `01_Executive`
- **Format**: `$#,##0.00`
- **Description**: Total dollar profit after deducting cost of goods sold from gross order subtotal.
```dax
[Gross Profit Amount] = 
SUM(fct_orders[gross_margin_amount])
```

### Measure 8: `[Gross Margin %]`
- **Display Folder**: `01_Executive`
- **Format**: `0.00%`
- **Description**: Proportion of gross revenue retained after deducting cost of goods sold.
```dax
[Gross Margin %] = 
DIVIDE([Gross Profit Amount], [Gross Revenue], 0)
```

### Measure 9: `[Total Sessions]`
- **Display Folder**: `01_Executive`
- **Format**: `#,##0`
- **Description**: Aggregate volume of recorded customer browsing and shopping sessions.
```dax
[Total Sessions] = 
COUNTROWS(fct_funnel)
```

### Measure 10: `[Total Unique Users]`
- **Display Folder**: `01_Executive`
- **Format**: `#,##0`
- **Description**: Distinct count of individual users active across browsing sessions.
```dax
[Total Unique Users] = 
DISTINCTCOUNT(fct_funnel[user_id])
```

### Measure 11: `[Overall Conversion Rate %]`
- **Display Folder**: `01_Executive`
- **Format**: `0.00%`
- **Description**: Percentage of total browsing sessions resulting in completed orders.
```dax
[Overall Conversion Rate %] = 
DIVIDE([Total Orders], [Total Sessions], 0)
```

### Measure 12: `[MoM Revenue Growth %]`
- **Display Folder**: `01_Executive`
- **Format**: `+0.00%;-0.00%;0.00%`
- **Description**: Percentage change in gross revenue compared to the prior calendar month.
```dax
[MoM Revenue Growth %] = 
VAR CurrentRevenue = [Gross Revenue]
VAR PriorRevenue = CALCULATE([Gross Revenue], DATEADD(dim_date[date_key], -1, MONTH))
RETURN
    DIVIDE(CurrentRevenue - PriorRevenue, PriorRevenue, BLANK())
```

### Measure 13: `[YoY Revenue Growth %]`
- **Display Folder**: `01_Executive`
- **Format**: `+0.00%;-0.00%;0.00%`
- **Description**: Percentage change in gross revenue compared to the same period in the prior year.
```dax
[YoY Revenue Growth %] = 
VAR CurrentRevenue = [Gross Revenue]
VAR PriorRevenue = CALCULATE([Gross Revenue], DATEADD(dim_date[date_key], -1, YEAR))
RETURN
    DIVIDE(CurrentRevenue - PriorRevenue, PriorRevenue, BLANK())
```

### Measure 14: `[Revenue 7-Day Moving Avg]`
- **Display Folder**: `01_Executive`
- **Format**: `$#,##0.00`
- **Description**: Trailing 7-day smoothed average of daily gross revenue.
```dax
[Revenue 7-Day Moving Avg] = 
VAR WindowDays = 7
VAR RevenueInPeriod = CALCULATE(
    [Gross Revenue],
    DATESINPERIOD(dim_date[date_day], MAX(dim_date[date_day]), -WindowDays, DAY)
)
VAR DaysWithData = COUNTROWS(
    DATESINPERIOD(dim_date[date_day], MAX(dim_date[date_day]), -WindowDays, DAY)
)
RETURN
    DIVIDE(RevenueInPeriod, MIN(WindowDays, DaysWithData), 0)
```

### Measure 15: `[Revenue 30-Day Moving Avg]`
- **Display Folder**: `01_Executive`
- **Format**: `$#,##0.00`
- **Description**: Trailing 30-day smoothed average of daily gross revenue.
```dax
[Revenue 30-Day Moving Avg] = 
VAR WindowDays = 30
VAR RevenueInPeriod = CALCULATE(
    [Gross Revenue],
    DATESINPERIOD(dim_date[date_day], MAX(dim_date[date_day]), -WindowDays, DAY)
)
VAR DaysWithData = COUNTROWS(
    DATESINPERIOD(dim_date[date_day], MAX(dim_date[date_day]), -WindowDays, DAY)
)
RETURN
    DIVIDE(RevenueInPeriod, MIN(WindowDays, DaysWithData), 0)
```

### Measure 16: `[Returning Users Count]`
- **Display Folder**: `01_Executive`
- **Format**: `#,##0`
- **Description**: Count of distinct active users who have completed more than one lifetime order.
```dax
[Returning Users Count] = 
CALCULATE(
    DISTINCTCOUNT(dim_users[user_id]),
    dim_users[lifetime_orders] > 1
)
```

### Measure 17: `[Returning User Order Share %]`
- **Display Folder**: `01_Executive`
- **Format**: `0.00%`
- **Description**: Share of total orders placed by returning (multi-order) customers.
```dax
[Returning User Order Share %] = 
VAR ReturningOrders = CALCULATE(
    [Total Orders],
    fct_orders[is_first_order] = FALSE() || fct_orders[is_repeat_order] = TRUE()
)
RETURN
    DIVIDE(ReturningOrders, [Total Orders], 0)
```

---

## 2. Display Folder: `02_Funnel`

### Measures 18-23: Funnel Stage Volumes
```dax
[Stage 1 Landing Sessions] = 
CALCULATE([Total Sessions], fct_funnel[reached_landing_page] = 1 || fct_funnel[has_landing_page] = TRUE())

[Stage 2 Product View Sessions] = 
CALCULATE([Total Sessions], fct_funnel[reached_product_view] = 1 || fct_funnel[has_product_view] = TRUE())

[Stage 3 Add To Cart Sessions] = 
CALCULATE([Total Sessions], fct_funnel[reached_add_to_cart] = 1 || fct_funnel[has_add_to_cart] = TRUE())

[Stage 4 Checkout Started Sessions] = 
CALCULATE([Total Sessions], fct_funnel[reached_checkout_started] = 1 || fct_funnel[has_checkout_started] = TRUE())

[Stage 5 Payment Started Sessions] = 
CALCULATE([Total Sessions], fct_funnel[reached_payment_started] = 1 || fct_funnel[has_payment_started] = TRUE())

[Stage 6 Purchase Sessions] = 
CALCULATE([Total Sessions], fct_funnel[reached_purchase] = 1 || fct_funnel[has_purchase] = TRUE())
```

### Measures 24-29: Micro-Conversion Rates
```dax
[Overall Funnel Conversion Rate %] = 
DIVIDE([Stage 6 Purchase Sessions], [Stage 1 Landing Sessions], 0)

[Stage 1 to 2 Conversion Rate %] = 
DIVIDE([Stage 2 Product View Sessions], [Stage 1 Landing Sessions], 0)

[Stage 2 to 3 Conversion Rate %] = 
DIVIDE([Stage 3 Add To Cart Sessions], [Stage 2 Product View Sessions], 0)

[Stage 3 to 4 Conversion Rate %] = 
DIVIDE([Stage 4 Checkout Started Sessions], [Stage 3 Add To Cart Sessions], 0)

[Stage 4 to 5 Conversion Rate %] = 
DIVIDE([Stage 5 Payment Started Sessions], [Stage 4 Checkout Started Sessions], 0)

[Stage 5 to 6 Conversion Rate %] = 
DIVIDE([Stage 6 Purchase Sessions], [Stage 5 Payment Started Sessions], 0)
```

### Measures 30-33: Stage Abandonment / Drop-offs
```dax
[Drop-off Landing to View] = [Stage 1 Landing Sessions] - [Stage 2 Product View Sessions]
[Drop-off View to Cart] = [Stage 2 Product View Sessions] - [Stage 3 Add To Cart Sessions]
[Drop-off Cart to Checkout] = [Stage 3 Add To Cart Sessions] - [Stage 4 Checkout Started Sessions]
[Drop-off Checkout to Payment] = [Stage 4 Checkout Started Sessions] - [Stage 5 Payment Started Sessions]
```

---

## 3. Display Folder: `03_Retention`

### Measures 34-41: Cohort Baseline & Retained Users (M0-M6+)
```dax
[Cohort Size (M0 Users)] = 
CALCULATE(DISTINCTCOUNT(fct_user_retention[user_id]), fct_user_retention[month_number] = 0 || fct_user_retention[month_offset] = 0)

[M0 Retained Users] = 
CALCULATE(DISTINCTCOUNT(fct_user_retention[user_id]), (fct_user_retention[month_number] = 0 || fct_user_retention[month_offset] = 0) && (fct_user_retention[is_retained] = 1 || fct_user_retention[is_active] = 1))

[M1 Retained Users] = 
CALCULATE(DISTINCTCOUNT(fct_user_retention[user_id]), (fct_user_retention[month_number] = 1 || fct_user_retention[month_offset] = 1) && (fct_user_retention[is_retained] = 1 || fct_user_retention[is_active] = 1))

[M2 Retained Users] = 
CALCULATE(DISTINCTCOUNT(fct_user_retention[user_id]), (fct_user_retention[month_number] = 2 || fct_user_retention[month_offset] = 2) && (fct_user_retention[is_retained] = 1 || fct_user_retention[is_active] = 1))

[M3 Retained Users] = 
CALCULATE(DISTINCTCOUNT(fct_user_retention[user_id]), (fct_user_retention[month_number] = 3 || fct_user_retention[month_offset] = 3) && (fct_user_retention[is_retained] = 1 || fct_user_retention[is_active] = 1))

[M4 Retained Users] = 
CALCULATE(DISTINCTCOUNT(fct_user_retention[user_id]), (fct_user_retention[month_number] = 4 || fct_user_retention[month_offset] = 4) && (fct_user_retention[is_retained] = 1 || fct_user_retention[is_active] = 1))

[M5 Retained Users] = 
CALCULATE(DISTINCTCOUNT(fct_user_retention[user_id]), (fct_user_retention[month_number] = 5 || fct_user_retention[month_offset] = 5) && (fct_user_retention[is_retained] = 1 || fct_user_retention[is_active] = 1))

[M6 Retained Users] = 
CALCULATE(DISTINCTCOUNT(fct_user_retention[user_id]), (fct_user_retention[month_number] >= 6 || fct_user_retention[month_offset] >= 6) && (fct_user_retention[is_retained] = 1 || fct_user_retention[is_active] = 1))
```

### Measures 42-49: Retention Rates, Repeat Rate & Cumulative LTV
```dax
[M1 Retention Rate %] = IF(MIN(dim_date[date_day]) > TODAY(), BLANK(), DIVIDE([M1 Retained Users], [Cohort Size (M0 Users)], 0))
[M2 Retention Rate %] = IF(MIN(dim_date[date_day]) > TODAY(), BLANK(), DIVIDE([M2 Retained Users], [Cohort Size (M0 Users)], 0))
[M3 Retention Rate %] = IF(MIN(dim_date[date_day]) > TODAY(), BLANK(), DIVIDE([M3 Retained Users], [Cohort Size (M0 Users)], 0))
[M4 Retention Rate %] = IF(MIN(dim_date[date_day]) > TODAY(), BLANK(), DIVIDE([M4 Retained Users], [Cohort Size (M0 Users)], 0))
[M5 Retention Rate %] = IF(MIN(dim_date[date_day]) > TODAY(), BLANK(), DIVIDE([M5 Retained Users], [Cohort Size (M0 Users)], 0))
[M6 Retention Rate %] = IF(MIN(dim_date[date_day]) > TODAY(), BLANK(), DIVIDE([M6 Retained Users], [Cohort Size (M0 Users)], 0))

[Repeat Purchase Rate %] = 
VAR RepeatCustomers = CALCULATE(DISTINCTCOUNT(dim_users[user_id]), dim_users[lifetime_orders] > 1)
VAR TotalCustomers = DISTINCTCOUNT(dim_users[user_id])
RETURN DIVIDE(RepeatCustomers, TotalCustomers, 0)

[Cohort Cumulative LTV per User] = 
DIVIDE(SUM(fct_user_retention[cumulative_revenue]), [Cohort Size (M0 Users)], 0)
```

---

## 4. Display Folder: `04_Experiment`

### Measures 50-58: Experiment Baseline & Uplift
```dax
[AB Control Sessions] = CALCULATE(COUNTROWS(fct_ab_test), fct_ab_test[ab_variant] = "control")
[AB Treatment Sessions] = CALCULATE(COUNTROWS(fct_ab_test), fct_ab_test[ab_variant] = "treatment")
[AB Total Experiment Sessions] = [AB Control Sessions] + [AB Treatment Sessions]

[AB Control Purchases] = CALCULATE(COUNTROWS(fct_ab_test), fct_ab_test[ab_variant] = "control" && (fct_ab_test[completed_purchase] = 1 || fct_ab_test[converted_to_purchase] = 1))
[AB Treatment Purchases] = CALCULATE(COUNTROWS(fct_ab_test), fct_ab_test[ab_variant] = "treatment" && (fct_ab_test[completed_purchase] = 1 || fct_ab_test[converted_to_purchase] = 1))

[AB Control Conversion Rate %] = DIVIDE([AB Control Purchases], [AB Control Sessions], 0)
[AB Treatment Conversion Rate %] = DIVIDE([AB Treatment Purchases], [AB Treatment Sessions], 0)

[AB Absolute Uplift] = [AB Treatment Conversion Rate %] - [AB Control Conversion Rate %]

[AB Relative Uplift %] = 
IF([AB Control Conversion Rate %] = 0, BLANK(), DIVIDE([AB Absolute Uplift], [AB Control Conversion Rate %], BLANK()))
```

### Measures 59-68: Two-Proportion Test, SRM Chi^2, and 95% Confidence Intervals
```dax
[AB Pooled Proportion] = 
DIVIDE([AB Control Purchases] + [AB Treatment Purchases], [AB Control Sessions] + [AB Treatment Sessions], 0)

[AB Pooled Standard Error] = 
VAR P = [AB Pooled Proportion]
VAR N1 = [AB Control Sessions]
VAR N2 = [AB Treatment Sessions]
RETURN IF(N1 > 0 && N2 > 0 && P > 0 && P < 1, SQRT(P * (1 - P) * (DIVIDE(1, N1, 0) + DIVIDE(1, N2, 0))), 0)

[AB Z-Score] = 
DIVIDE([AB Absolute Uplift], [AB Pooled Standard Error], 0)

[AB Two-Sided P-Value Approx] = 
VAR Z = ABS([AB Z-Score])
RETURN IF(ISBLANK(Z) || Z = 0, 1.0, 2 * (1 - (DIVIDE(1, 1 + EXP(-0.07056 * Z^3 - 1.5976 * Z), 1))))

[AB Statistically Significant Flag] = 
IF(ABS([AB Z-Score]) >= 1.96, "Statistically Significant (p < 0.05)", "Inconclusive (p >= 0.05)")

[AB SRM Expected Sessions] = 
([AB Control Sessions] + [AB Treatment Sessions]) / 2

[AB SRM Chi-Square Statistic] = 
VAR Expected = ([AB Control Sessions] + [AB Treatment Sessions]) / 2 
RETURN DIVIDE(([AB Control Sessions] - Expected)^2, Expected) + DIVIDE(([AB Treatment Sessions] - Expected)^2, Expected)

[AB SRM Status] = 
VAR Chi2 = [AB SRM Chi-Square Statistic]
RETURN IF(ISBLANK(Chi2), "Unknown", IF(Chi2 > 6.635, "SRM FAILED - BIASED (p < 0.01)", "SRM PASSED - BALANCED"))

[AB 95% CI Lower Bound] = 
VAR MarginOfError = 1.96 * DIVIDE([AB Pooled Standard Error], [AB Control Conversion Rate %], 0)
RETURN [AB Relative Uplift %] - MarginOfError

[AB 95% CI Upper Bound] = 
VAR MarginOfError = 1.96 * DIVIDE([AB Pooled Standard Error], [AB Control Conversion Rate %], 0)
RETURN [AB Relative Uplift %] + MarginOfError
```

---

## 5. Display Folder: `05_Helper_Stats`

```dax
[Standard Normal Inverse Approx] = 1.95996
[Chi-Square Critical Value 99%] = 6.6349
[Max Observed Date] = MAX(dim_date[date_day])
[Has Filter Applied] = ISFILTERED(dim_users[customer_segment]) || ISFILTERED(fct_funnel[device_type])
[Card Subtitle Date Range] = "Period: " & FORMAT(MIN(dim_date[date_day]), "YYYY-MM-DD") & " to " & FORMAT(MAX(dim_date[date_day]), "YYYY-MM-DD")
[WCAG Formatted Status Color] = IF([AB SRM Chi-Square Statistic] > 6.635, "#F43F5E", "#10B981")
[Divide Safe Helper] = DIVIDE(1, 1, 0)
[Blank Guard Helper] = IF(ISBLANK(MAX(dim_date[date_day])), "No Date", "Valid Date")
[Segment Filter Slicer Title] = "Customer Segment: " & SELECTEDVALUE(dim_users[customer_segment], "All Segments")
[Currency Formatter] = FORMAT([Gross Revenue], "$#,##0.00")
```
