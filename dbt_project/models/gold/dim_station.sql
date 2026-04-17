with stations as (
    select
        cast(start_station_id as text) as station_id,
        start_station_name as station_name
    from {{ ref('stg_trips') }}

    union all

    select
        cast(end_station_id as text) as station_id,
        end_station_name as station_name
    from {{ ref('stg_trips') }}
)
select distinct
    {{ dbt_utils.generate_surrogate_key(['station_id', 'station_name']) }} as station_key,
    station_id,
    station_name
from stations
where station_id is not null
  and station_name is not null
