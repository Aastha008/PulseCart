-- PulseCart BigQuery SQL Compatibility Macros for Local Verification & Multi-Engine Execution

{% macro timestamp_diff_macro() %}
-- Registers DuckDB compatibility macro for BigQuery TIMESTAMP_DIFF
CREATE OR REPLACE MACRO TIMESTAMP_DIFF(end_ts, start_ts, unit) AS 
    datediff(unit, start_ts, end_ts);
{% endmacro %}

{% macro safe_divide_macro() %}
-- Registers DuckDB compatibility macro for BigQuery SAFE_DIVIDE
CREATE OR REPLACE MACRO SAFE_DIVIDE(num, denom) AS 
    CASE WHEN denom = 0 THEN NULL ELSE num / denom END;
{% endmacro %}

{% macro logical_or_macro() %}
-- Registers DuckDB compatibility macro for BigQuery LOGICAL_OR
CREATE OR REPLACE MACRO LOGICAL_OR(val) AS 
    bool_or(val);
{% endmacro %}
