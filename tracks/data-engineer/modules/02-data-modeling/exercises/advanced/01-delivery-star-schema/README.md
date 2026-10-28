---
title: Thiết kế và xây star schema cho phân tích giao hàng Olist
level: advanced
services: []
files:
  - path: starter/design.md
    note: Viết thiết kế (grain, bus matrix, SCD)
  - path: starter/build.sql
    note: Xây dimension và fact
  - path: tests/test_delivery_mart.py
    note: Không sửa, chỉ kiểm hợp đồng tối thiểu
run:
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/advanced/01-delivery-star-schema -q
---

## Mục tiêu

Tự đi trọn bốn bước Kimball cho một quy trình nghiệp vụ thật (giao hàng), ra quyết định về grain,
loại fact, role-playing dimension, SCD, và hiện thực bằng SQL chạy được.

## Đề bài

Đội vận hành Olist muốn trả lời:

- Tỷ lệ đơn giao trễ (so với ngày hẹn) theo bang của khách, theo seller, theo tháng mua.
- Thời gian trung bình từng chặng: mua → duyệt, duyệt → giao cho đơn vị vận chuyển, vận chuyển → tới khách.
- Đơn trễ có review thấp hơn không?

Dữ liệu nguồn (test tạo sẵn trong DuckDB, cùng tên cột với bộ Olist):
`raw_orders(order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at,
order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date)`,
`raw_order_items(order_id, order_item_id, product_id, seller_id, price, freight_value)`,
`raw_customers(customer_id, customer_city, customer_state)`,
`raw_sellers(seller_id, seller_city, seller_state)`,
`raw_reviews(review_id, order_id, review_score)`.

1. Viết `starter/design.md`: business process, grain, loại fact (transaction / accumulating
   snapshot), danh sách dimension và measure, bus matrix, quyết định SCD cho từng dimension, cách
   xử lý đơn nhiều seller, đơn chưa giao, đơn nhiều review, và các câu SQL trả lời 3 câu hỏi trên.
2. Viết `starter/build.sql` xây mô hình. Bạn được tự do thêm bảng/cột, nhưng phải có **hợp đồng tối
   thiểu** sau để test và dashboard dùng được:
   - `dim_date(date_key INTEGER, full_date DATE, ...)` với `date_key` dạng `YYYYMMDD`, phủ mọi ngày xuất hiện trong dữ liệu.
   - `dim_customer(customer_key, customer_id, city, state, ...)`.
   - `fact_order_delivery`, **một dòng cho mỗi đơn đã giao** (`order_status = 'delivered'` và có
     `order_delivered_customer_date`), với các cột: `order_id`, `customer_key`,
     `purchase_date_key`, `delivered_date_key`, `estimated_date_key`, `delivery_days` (số ngày lịch
     từ ngày mua tới ngày giao), `is_late` (ngày giao > ngày hẹn, so theo ngày), `items_count`,
     `total_freight`, `review_score` (trung bình nếu nhiều review, NULL nếu không có).

## Tiêu chí đạt

- Test hợp đồng tối thiểu pass (grain, khoá, giá trị đo trên dữ liệu mẫu, toàn vẹn tham chiếu).
- `design.md` trả lời đủ các quyết định thiết kế ở trên, có lý do và đánh đổi.
- Có SQL cho ba câu hỏi nghiệp vụ, chạy được trên mô hình của bạn.
- Xem rubric chi tiết trong lời giải.

## Gợi ý

### Gợi ý 1

Đơn hàng có nhiều mốc thời gian và được "đi tiếp" theo thời gian: đó là dấu hiệu của
**accumulating snapshot**. `dim_date` đóng nhiều vai (role-playing): purchase, delivered, estimated.

### Gợi ý 2

Tổng hợp `raw_order_items` và `raw_reviews` về grain đơn hàng **trước** khi join với `raw_orders`,
nếu không số dòng sẽ bị nhân lên. `date_diff('day', CAST(a AS DATE), CAST(b AS DATE))` cho số ngày lịch.
