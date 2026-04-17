with labels as (
    select distinct
        {{ classify_duration('duration_seconds') }} as bucket_label
    from {{ ref('stg_trips') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['bucket_label']) }} as duration_bucket_key,
    bucket_label
from labels
