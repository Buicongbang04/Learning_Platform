{% snapshot customers_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='customer_id',
        strategy='timestamp',
        updated_at='updated_at'
    )
}}

select
    customer_id,
    customer_city,
    customer_state,
    cast(updated_at as timestamp) as updated_at
from {{ source('olist', 'customers') }}

{% endsnapshot %}
