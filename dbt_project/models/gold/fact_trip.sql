with base as (
    select
        rental_id,
        start_datetime,
        end_datetime,
        start_station_id,
        start_station_name,
        end_station_id,
        end_station_name,
        duration_seconds,
        date_trunc('hour', start_datetime) as full_date,
        {{ classify_duration('duration_seconds') }} as bucket_label
    from {{ ref('stg_trips') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['rental_id']) }} as trip_key,
    b.rental_id,
    s_start.station_key as start_station_key,
    s_end.station_key as end_station_key,
    d.date_key,
    bucket.duration_bucket_key,
    b.duration_seconds,
    b.start_datetime,
    b.end_datetime
from base b
left join {{ ref('dim_station') }} s_start
    on cast(b.start_station_id as text) = s_start.station_id
   and b.start_station_name = s_start.station_name
left join {{ ref('dim_station') }} s_end
    on cast(b.end_station_id as text) = s_end.station_id
   and b.end_station_name = s_end.station_name
left join {{ ref('dim_date') }} d
    on b.full_date = d.full_date
left join {{ ref('dim_duration_bucket') }} bucket
    on b.bucket_label = bucket.bucket_label
