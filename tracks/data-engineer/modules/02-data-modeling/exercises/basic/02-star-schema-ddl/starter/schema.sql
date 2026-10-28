-- Star schema cho quy trình bán hàng của Olist. Grain: một item trong một đơn hàng.

-- TODO 1: CREATE TABLE dim_date (date_key PK dạng YYYYMMDD, full_date, year, quarter, month, day,
--         day_of_week (ISO, thứ Hai = 1), is_weekend)

-- TODO 2: đổ dim_date cho mọi ngày từ 2017-01-01 tới 2018-12-31

-- TODO 3: CREATE TABLE dim_customer (customer_key PK, customer_id, city, state)

-- TODO 4: CREATE TABLE dim_product (product_key PK, product_id, category_name)

-- TODO 5: CREATE TABLE dim_seller (seller_key PK, seller_id, city, state)

-- TODO 6: CREATE TABLE fact_order_items với PK (order_id, order_item_id) và 4 FOREIGN KEY

SELECT 1;
