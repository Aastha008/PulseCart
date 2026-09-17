-- ==============================================================================
-- PulseCart Cross-Warehouse Compatibility Macros
-- Supports BigQuery, Snowflake, and DuckDB simultaneously without SQL duplication.
-- ==============================================================================

{# --- 1. TIMESTAMP & DATE DIFFERENCE --- #}
{% macro datediff_cross(start_ts, end_ts, datepart) %}
  {% if target.type == 'bigquery' %}
    TIMESTAMP_DIFF({{ end_ts }}, {{ start_ts }}, {{ datepart }})
  {% elif target.type == 'snowflake' %}
    DATEDIFF({{ datepart }}, {{ start_ts }}, {{ end_ts }})
  {% else %}
    DATEDIFF('{{ datepart }}', {{ start_ts }}, {{ end_ts }})
  {% endif %}
{% endmacro %}

{# --- 2. DATE TRUNCATION --- #}
{% macro date_trunc_cross(date_expr, datepart) %}
  {% if target.type == 'bigquery' %}
    DATE_TRUNC({{ date_expr }}, {{ datepart }})
  {% elif target.type == 'snowflake' %}
    DATE_TRUNC('{{ datepart }}', {{ date_expr }})
  {% else %}
    DATE_TRUNC('{{ datepart }}', {{ date_expr }})
  {% endif %}
{% endmacro %}

{# --- 3. SAFE DIVISION --- #}
{% macro safe_divide_cross(num, denom) %}
  CASE WHEN ({{ denom }}) = 0 OR ({{ denom }}) IS NULL THEN NULL ELSE ({{ num }}) / ({{ denom }}) END
{% endmacro %}

{# --- 4. DATE/TIMESTAMP SUBTRACTION --- #}
{% macro date_sub_days_cross(ts, days) %}
  {% if target.type == 'bigquery' %}
    TIMESTAMP_SUB({{ ts }}, INTERVAL {{ days }} DAY)
  {% elif target.type == 'snowflake' %}
    DATEADD(day, -{{ days }}, {{ ts }})
  {% else %}
    {{ ts }} - INTERVAL {{ days }} DAY
  {% endif %}
{% endmacro %}
