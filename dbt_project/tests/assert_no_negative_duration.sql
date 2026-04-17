select *
from {{ ref('fact_trip') }}
where duration_seconds < 0
