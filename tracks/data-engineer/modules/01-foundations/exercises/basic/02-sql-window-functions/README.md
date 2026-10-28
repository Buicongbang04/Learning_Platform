---
title: Window function trên đơn hàng Olist (DuckDB)
level: basic
services: []
files:
  - path: starter/top_sellers.sql
    note: 1 TODO
  - path: starter/daily_revenue.sql
    note: 1 TODO
  - path: starter/customer_order_gaps.sql
    note: 1 TODO
  - path: tests/test_windows.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/basic/02-sql-window-functions -q
---

## Mục tiêu

Dùng thành thạo ba nhóm window function hay gặp nhất trong pipeline: xếp hạng (top-N mỗi nhóm),
tổng hợp có frame (luỹ kế, trung bình trượt) và dịch dòng (`LAG`).

## Đề bài

Test tạo sẵn trong DuckDB các bảng:

- `orders(order_id, customer_id, order_status, order_purchase_timestamp TIMESTAMP)`
- `order_items(order_id, order_item_id, seller_id, price DECIMAL(10,2))`
- `sellers(seller_id, seller_state)`

Mỗi tệp `.sql` chứa **một** câu `SELECT` (có thể có `WITH`). Viết:

1. **`top_sellers.sql`**: doanh thu (`SUM(price)`, chỉ tính đơn `order_status = 'delivered'`) của
   mỗi seller, xếp hạng trong từng bang bằng `DENSE_RANK` theo doanh thu giảm dần. Giữ các seller
   có hạng ≤ 2. Cột: `seller_state, seller_id, revenue, rnk`. Sắp xếp theo
   `seller_state, rnk, seller_id`.
2. **`daily_revenue.sql`**: doanh thu theo ngày mua (`CAST(order_purchase_timestamp AS DATE)`),
   chỉ đơn `delivered`, chỉ những ngày có đơn. Cột:
   - `order_date`, `revenue`,
   - `mtd_revenue`: luỹ kế từ đầu tháng tới ngày đó (reset mỗi tháng),
   - `ma3`: trung bình của 3 **dòng** gần nhất (dòng hiện tại và 2 dòng trước, ít hơn nếu đầu bảng),
     làm tròn 2 chữ số.

   Sắp xếp theo `order_date`.
3. **`customer_order_gaps.sql`**: với mỗi đơn hàng (mọi trạng thái): `customer_id, order_id,
   order_purchase_timestamp, order_seq, days_since_prev`. `order_seq` là số thứ tự đơn của khách đó
   (1, 2, 3… theo thời gian mua), `days_since_prev` là số ngày (`date_diff('day', ...)` trên phần
   ngày) kể từ đơn trước của cùng khách, `NULL` với đơn đầu tiên. Sắp xếp theo
   `customer_id, order_seq`.

## Tiêu chí đạt

- Ba truy vấn trả đúng cột, đúng thứ tự, đúng giá trị trên dữ liệu test.
- `top_sellers` xử lý đúng trường hợp hai seller bằng doanh thu (cùng hạng).
- `mtd_revenue` reset về đầu mỗi tháng; `ma3` dùng frame theo dòng.
- Dùng window function, không dùng self-join hay subquery tương quan.

## Gợi ý

### Gợi ý 1

Window function không đặt được trong `WHERE`. Tính hạng trong CTE rồi lọc ở ngoài, hoặc dùng
`QUALIFY rnk <= 2` (DuckDB hỗ trợ).

### Gợi ý 2

```sql
SUM(revenue) OVER (PARTITION BY date_trunc('month', order_date) ORDER BY order_date)
AVG(revenue) OVER (ORDER BY order_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
date_diff('day', CAST(LAG(ts) OVER (...) AS DATE), CAST(ts AS DATE))
```
