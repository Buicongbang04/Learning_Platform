# Lời giải: star schema cho phân tích giao hàng Olist

Bài này không có một đáp án duy nhất. Dưới đây là một thiết kế tham khảo, các quyết định cần cân
nhắc, và rubric chấm.

## Hướng làm

### 1. Business process và grain

- Process: **hoàn tất đơn hàng** (order fulfillment), từ lúc mua tới lúc khách nhận.
- Fact chính `fact_order_delivery`: **accumulating snapshot**, grain **một dòng / đơn hàng**. Các
  mốc (purchase, approved, carrier, delivered, estimated) là các cột date key; dòng được cập nhật khi
  đơn đi qua mốc mới. Hợp đồng của bài chỉ yêu cầu đơn đã giao, nhưng trong thực tế nên giữ cả đơn
  đang đi (mốc chưa tới = key `-1`/NULL) để theo dõi backlog.
- Fact phụ `fact_order_items` (transaction fact, grain item) cho câu hỏi theo seller/sản phẩm.

### 2. Dimension

| Dimension | Vai trò | SCD | Lý do |
| --- | --- | --- | --- |
| `dim_date` | purchase / approved / carrier / delivered / estimated (role-playing) | Không đổi | Sinh bằng `generate_series` |
| `dim_customer` | Nơi giao hàng | Type 2 trên city/state | Phân tích trễ theo **nơi ở lúc mua** |
| `dim_seller` | Nơi gửi hàng | Type 2 hoặc 1 | Seller đổi kho ảnh hưởng thời gian giao |
| `dim_product` | Danh mục, kích thước, cân nặng | Type 1 | Sửa danh mục là sửa lỗi |
| `dim_geolocation` (tuỳ chọn) | Zip prefix → lat/lng, vùng | Type 1 | Tính khoảng cách seller–khách |

### 3. Measure trên fact_order_delivery

`delivery_days`, `is_late`, `delay_days` (giao − hẹn, có thể âm), `approval_hours`,
`handling_days` (duyệt → giao vận chuyển), `shipping_days` (vận chuyển → khách), `items_count`,
`total_price`, `total_freight`, `seller_count`, `review_score`. `is_late` lưu dạng boolean/0-1 để
`AVG(is_late::int)` ra tỷ lệ; không lưu tỷ lệ đã tính sẵn (non-additive).

### 4. Bus matrix

| Process \ Dimension | date | customer | seller | product | geolocation |
| --- | --- | --- | --- | --- | --- |
| Order items (bán hàng) | x | x | x | x | x |
| Order delivery (giao hàng) | x (5 vai) | x | x (seller chính) |  | x |
| Payments | x | x |  |  |  |
| Reviews | x | x | x |  |  |

### 5. Các trường hợp đặc biệt cần nêu

- **Đơn nhiều seller**: grain đơn hàng không gắn được một seller duy nhất. Lựa chọn: (a) seller có
  giá trị lớn nhất làm "primary seller" + cột `seller_count`; (b) đổi grain thành (order, seller)
  vì Olist thực tế tách kiện theo seller; (c) bridge table. Phải nêu rõ và nhất quán.
- **Đơn chưa giao/huỷ**: không vào hợp đồng tối thiểu, nhưng thiết kế nên nói cách theo dõi (dòng
  với mốc NULL, cờ `is_canceled`).
- **Nhiều review**: tổng hợp về grain đơn (trung bình, hoặc review mới nhất) **trước** khi join.
- **Dữ liệu bất thường**: delivered < purchase, carrier < approved → data quality test, gắn cờ thay vì âm thầm loại.
- **Trễ tính theo ngày lịch** (so `DATE`), vì ngày hẹn của Olist chỉ có phần ngày.

### SQL tham khảo cho build.sql (DuckDB)

`dim_customer` ở đây là SCD2 "khởi tạo" (mọi khách một phiên bản); pipeline thật dùng merge SCD2 từ
bài intermediate.

```sql
CREATE TABLE dim_date AS
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key, d AS full_date,
       year(d) AS year, quarter(d) AS quarter, month(d) AS month, isodow(d) AS day_of_week, isodow(d) IN (6,7) AS is_weekend
FROM (SELECT CAST(ts AS DATE) d FROM generate_series(
        (SELECT CAST(MIN(order_purchase_timestamp) AS DATE) FROM raw_orders)::TIMESTAMP,
        (SELECT GREATEST(MAX(order_delivered_customer_date), MAX(order_estimated_delivery_date)) FROM raw_orders)::DATE::TIMESTAMP,
        INTERVAL 1 DAY) t(ts));
CREATE TABLE dim_customer AS
SELECT row_number() OVER (ORDER BY customer_id) AS customer_key, customer_id, customer_city AS city, customer_state AS state,
       DATE '1900-01-01' AS valid_from, DATE '9999-12-31' AS valid_to, TRUE AS is_current
FROM raw_customers;
CREATE TABLE fact_order_delivery AS
WITH items AS (SELECT order_id, COUNT(*) items_count, SUM(price) total_price, SUM(freight_value) total_freight,
                      COUNT(DISTINCT seller_id) seller_count FROM raw_order_items GROUP BY 1),
     reviews AS (SELECT order_id, AVG(review_score) review_score FROM raw_reviews GROUP BY 1),
     o AS (SELECT * FROM raw_orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL)
SELECT o.order_id, c.customer_key,
       CAST(strftime(o.order_purchase_timestamp, '%Y%m%d') AS INTEGER) purchase_date_key,
       CAST(strftime(o.order_delivered_customer_date, '%Y%m%d') AS INTEGER) delivered_date_key,
       CAST(strftime(o.order_estimated_delivery_date, '%Y%m%d') AS INTEGER) estimated_date_key,
       date_diff('day', CAST(o.order_purchase_timestamp AS DATE), CAST(o.order_delivered_customer_date AS DATE)) delivery_days,
       CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE) is_late,
       date_diff('hour', o.order_purchase_timestamp, o.order_approved_at) approval_hours,
       date_diff('day', CAST(o.order_approved_at AS DATE), CAST(o.order_delivered_carrier_date AS DATE)) handling_days,
       date_diff('day', CAST(o.order_delivered_carrier_date AS DATE), CAST(o.order_delivered_customer_date AS DATE)) shipping_days,
       COALESCE(i.items_count, 0) items_count, i.total_price, COALESCE(i.total_freight, 0) total_freight, i.seller_count,
       r.review_score
FROM o
JOIN dim_customer c ON c.customer_id = o.customer_id AND c.is_current
LEFT JOIN items i ON i.order_id = o.order_id
LEFT JOIN reviews r ON r.order_id = o.order_id;
```

### SQL trả lời câu hỏi

```sql
-- 1. Tỷ lệ trễ theo bang khách và tháng mua
SELECT c.state, d.year, d.month,
       COUNT(*) AS orders, AVG(CAST(f.is_late AS INTEGER)) AS late_rate
FROM fact_order_delivery f
JOIN dim_customer c ON c.customer_key = f.customer_key
JOIN dim_date d ON d.date_key = f.purchase_date_key
GROUP BY ALL ORDER BY late_rate DESC;

-- 2. Thời gian từng chặng
SELECT AVG(approval_hours) AS avg_approval_h, AVG(handling_days) AS avg_handling_d,
       AVG(shipping_days) AS avg_shipping_d, AVG(delivery_days) AS avg_total_d
FROM fact_order_delivery;

-- 3. Review theo trễ / không trễ
SELECT is_late, COUNT(*) AS orders, AVG(review_score) AS avg_review
FROM fact_order_delivery GROUP BY is_late;
```

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt tốt khi |
| --- | --- | --- |
| Test hợp đồng tối thiểu pass | 20 | 4/4 test pass |
| Grain và loại fact | 15 | Nêu rõ grain một câu; nhận ra accumulating snapshot; giải thích vì sao không dùng grain item cho measure giao hàng |
| Dimension và SCD | 15 | Role-playing `dim_date`; chọn SCD có lý do theo câu hỏi nghiệp vụ; surrogate key |
| Xử lý trường hợp đặc biệt | 15 | Đơn nhiều seller, đơn chưa giao/huỷ, nhiều review, dữ liệu ngày bất thường; có lựa chọn và đánh đổi |
| Tránh double counting | 10 | Tổng hợp items/reviews về grain đơn trước khi join; kiểm chứng số dòng |
| SQL trả lời 3 câu hỏi | 15 | Chạy được, đúng grain, tỷ lệ tính từ tử/mẫu chứ không trung bình các tỷ lệ |
| Bus matrix, khả năng mở rộng | 10 | Conformed dimension dùng chung với fact bán hàng/review; nói cách nạp incremental và cập nhật dòng accumulating |

Mức đạt: ≥ 70 điểm và toàn bộ test pass.
