-- Chuẩn hoá orders_flat về 3NF.
-- Bảng orders_flat đã có sẵn khi script này chạy (DuckDB).

-- TODO 1: tạo bảng customers(customer_id PK, customer_city, customer_state) và đổ dữ liệu

-- TODO 2: tạo bảng sellers(seller_id PK, seller_city, seller_state) và đổ dữ liệu

-- TODO 3: tạo bảng products(product_id PK, product_category_name) và đổ dữ liệu

-- TODO 4: tạo bảng orders(order_id PK, customer_id FK, order_status, order_purchase_timestamp)

-- TODO 5: tạo bảng order_items với PK (order_id, order_item_id) và FK tới orders, products, sellers

SELECT 1;
