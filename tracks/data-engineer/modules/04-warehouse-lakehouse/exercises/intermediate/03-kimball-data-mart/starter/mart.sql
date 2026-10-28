-- Star schema cho mart bán hàng. Chạy tuần tự từng câu lệnh.

-- TODO 1: CREATE OR REPLACE TABLE dim_customer AS ... (surrogate key + unknown member key 0)

-- TODO 2: CREATE OR REPLACE TABLE dim_product AS ... (category NULL -> 'unknown', unknown member key 0)

-- TODO 3: CREATE OR REPLACE TABLE dim_date AS ... (liên tục từ min tới max ngày mua)

-- TODO 4: CREATE OR REPLACE TABLE fact_order_items AS ... (grain: một dòng mỗi item)

SELECT 1 AS todo;
