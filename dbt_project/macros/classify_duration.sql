{% macro classify_duration(duration_seconds) %}
    case
        when {{ duration_seconds }} < 600 then 'curta'
        when {{ duration_seconds }} <= 1800 then 'media'
        else 'longa'
    end
{% endmacro %}
