with base as (
    select distinct
        date_trunc('hour', start_datetime) as full_date
    from {{ ref('stg_trips') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['full_date']) }} as date_key,
    full_date,
    extract(dow from full_date)::int as day_of_week,
    to_char(full_date, 'Dy') as day_name,
    extract(hour from full_date)::int as hour,
    extract(week from full_date)::int as week_number,
    extract(month from full_date)::int as month,
    extract(year from full_date)::int as year,
    case when extract(isodow from full_date) in (6, 7) then true else false end as is_weekend
from base
