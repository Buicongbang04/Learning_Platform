-- Staging: đổi tên, ép kiểu, gắn cờ. Không lọc dòng nào: mọi quyết định "dòng nào tính" nằm ở mart.
select
    source_row                                   as line_id,
    cast("Invoice" as varchar)                   as invoice_no,
    cast("StockCode" as varchar)                 as stock_code,
    trim(cast("Description" as varchar))         as description,
    cast("Quantity" as integer)                  as quantity,
    cast("Price" as double)                      as unit_price,
    cast("Customer ID" as bigint)                as customer_id,
    "Country"                                    as country,
    cast("InvoiceDate" as timestamp)             as invoiced_at,
    cast("InvoiceDate" as date)                  as invoice_date,
    starts_with(cast("Invoice" as varchar), 'C') as is_cancellation,
    -- TODO: dòng bán hợp lệ theo định nghĩa chung: không phải hoá đơn C..., Quantity > 0 và Price > 0
    false                                        as is_valid_sale
from {{ source('raw', 'sales_lines') }}
