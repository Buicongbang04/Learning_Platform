-- Chuỗi tháng hoạt động LIÊN TIẾP của mỗi seller (gaps-and-islands). Bảng: orders, order_items.
-- Tháng hoạt động: tháng mua (order_purchase_timestamp) có ít nhất một đơn giao xong chứa món của seller,
-- chỉ lấy đơn mua trước 2018-09-01.
-- Kết quả: seller_id, start_month (DATE), end_month (DATE), n_months; sắp theo seller_id, start_month.
-- TODO: CTE active (seller_id, month) không trùng
-- TODO: CTE grouped: số thứ tự tháng - ROW_NUMBER() là hằng số trong một chuỗi liên tiếp
-- TODO: gom theo (seller_id, nhóm)
SELECT NULL::VARCHAR AS seller_id, NULL::DATE AS start_month, NULL::DATE AS end_month, NULL::BIGINT AS n_months
WHERE FALSE;
