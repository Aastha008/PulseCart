{# 
    PulseCart Custom Schema Naming Macro
    Ensures models with custom schemas (e.g. staging, intermediate, marts)
    are placed directly into their dedicated schema names rather than being 
    prefixed with the default target schema (e.g. ANALYTICS_STAGING).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
