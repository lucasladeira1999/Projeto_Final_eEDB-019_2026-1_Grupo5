with source as (
    select
        rental_id,
        start_date,
        end_date,
        start_station_id,
        end_station_id,
        start_station_name,
        end_station_name,
        duration,
        bike_id
    from raw.trips
),
cleaned as (
    select
        cast(rental_id as bigint) as rental_id,
        cast(start_date as timestamp) as start_datetime,
        cast(end_date as timestamp) as end_datetime,
        cast(start_station_id as integer) as start_station_id,
        cast(end_station_id as integer) as end_station_id,
        nullif(trim(start_station_name), '') as start_station_name,
        nullif(trim(end_station_name), '') as end_station_name,
        cast(duration as integer) as duration_seconds,
        cast(bike_id as bigint) as bike_id
    from source
)
select
    rental_id,
    start_datetime,
    end_datetime,
    start_station_id,
    end_station_id,
    start_station_name,
    end_station_name,
    duration_seconds,
    bike_id,
    date_trunc('hour', start_datetime) as trip_hour,
    extract(dow from start_datetime)::int as day_of_week,
    extract(week from start_datetime)::int as week_number,
    extract(month from start_datetime)::int as month_number,
    extract(year from start_datetime)::int as year_number
from cleaned
where duration_seconds >= 0
  and rental_id is not null
  and start_datetime is not null
  and end_datetime is not null
  and start_station_id is not null
  and end_station_id is not null
