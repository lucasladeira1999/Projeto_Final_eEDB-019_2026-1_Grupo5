select f.*
from {{ ref('fact_trip') }} f
left join {{ ref('dim_station') }} ds_start on f.start_station_key = ds_start.station_key
left join {{ ref('dim_station') }} ds_end on f.end_station_key = ds_end.station_key
where ds_start.station_key is null
   or ds_end.station_key is null
