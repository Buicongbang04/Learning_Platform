-- TODO: snapshot SCD Type 2 cho source('olist', 'customers'):
--   * target_schema='snapshots', unique_key='customer_id'
--   * strategy='timestamp', updated_at='updated_at'
--   * select customer_id, customer_city, customer_state, cast(updated_at as timestamp) as updated_at
{% snapshot customers_snapshot %}

{{ config(target_schema='snapshots') }}

select * from {{ source('olist', 'customers') }}

{% endsnapshot %}
