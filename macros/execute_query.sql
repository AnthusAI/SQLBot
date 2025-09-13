{% macro execute_raw_query(query) %}
  {# Check if this is a SELECT query or DML/DDL #}
  {% set query_upper = query.upper().strip() %}
  
  {% if query_upper.startswith('SELECT') or query_upper.startswith('WITH') or 'SELECT' in query_upper %}
    {# Use run_query for SELECT statements #}
    {% set result = run_query(query) %}
    {% if result and result.rows %}
      {% for row in result %}
        {{ log('ROW_DATA=' ~ row.values() | join('|'), info=true) }}
      {% endfor %}
      {{ log('COLUMN_NAMES=' ~ result.column_names | join('|'), info=true) }}
    {% else %}
      {{ log('COLUMN_NAMES=', info=true) }}
      {{ log('ROW_DATA=', info=true) }}
    {% endif %}
  {% else %}
    {# Use adapter.execute for DML/DDL operations #}
    {% set result = adapter.execute(query) %}
    {% if result %}
      {{ log('DML_SUCCESS=true', info=true) }}
      {{ log('COLUMN_NAMES=rows_affected', info=true) }}
      {{ log('ROW_DATA=1', info=true) }}
    {% else %}
      {{ log('DML_FAILED=true', info=true) }}
      {{ log('COLUMN_NAMES=error', info=true) }}
      {{ log('ROW_DATA=Execution failed', info=true) }}
    {% endif %}
  {% endif %}
{% endmacro %}