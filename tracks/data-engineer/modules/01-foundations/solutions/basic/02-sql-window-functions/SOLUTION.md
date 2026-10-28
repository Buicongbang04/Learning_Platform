# Lời giải: Window function trên đơn hàng Olist

## top_sellers.sql

Tách thành hai bước bằng CTE: tổng doanh thu theo `(seller_state, seller_id)` rồi xếp hạng. Không
lọc hạng trong cùng `SELECT` được vì window function tính *sau* `WHERE` (xem thứ tự thực thi logic
trong README). Trên DuckDB có thể viết gọn:

```sql
SELECT ..., DENSE_RANK() OVER (PARTITION BY seller_state ORDER BY revenue DESC) AS rnk
FROM seller_revenue
QUALIFY rnk <= 2
```

Vì sao `DENSE_RANK`: s1 và s2 cùng 100 nên cùng hạng 1, s3 (70) là hạng 2. Với `RANK`, s3 sẽ thành
hạng 3 và bị loại; với `ROW_NUMBER`, một trong hai seller bằng doanh thu bị đẩy xuống hạng 2 một cách
tuỳ ý. "Top-N" trong yêu cầu nghiệp vụ cần hỏi rõ xử lý hoà thế nào.

Lọc `order_status = 'delivered'` phải join `orders`; đơn `o4` (canceled, 500) không được tính.

## daily_revenue.sql

- Tổng theo ngày trong CTE trước, rồi window trên kết quả đã gộp (window chạy sau `GROUP BY`).
- `mtd_revenue`: `PARTITION BY date_trunc('month', order_date)` làm luỹ kế reset mỗi tháng.
- `ma3`: `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` lấy 3 **dòng**. Lưu ý ngày 2018-02-02 không có
  đơn nên "3 dòng" khác "3 ngày". Nếu cần đúng 3 ngày lịch, dùng
  `RANGE BETWEEN INTERVAL 2 DAY PRECEDING AND CURRENT ROW`, hoặc LEFT JOIN với date spine
  (bài intermediate 01).
- Ghi rõ frame cho `mtd_revenue` (`ROWS ... UNBOUNDED PRECEDING`): mặc định là `RANGE`, cho kết quả
  giống ở đây vì mỗi ngày một dòng, nhưng khác khi có giá trị `ORDER BY` trùng.

## customer_order_gaps.sql

- Mệnh đề `WINDOW w AS (...)` đặt tên cửa sổ dùng lại cho cả `ROW_NUMBER` và `LAG`, tránh lặp và
  tránh hai cửa sổ vô tình khác nhau.
- Thêm `order_id` vào `ORDER BY` của cửa sổ để thứ tự xác định khi hai đơn trùng thời gian.
- `LAG` trả `NULL` cho dòng đầu, nên `date_diff` cũng ra `NULL`, đúng yêu cầu.
- Đổi sang `DATE` trước khi tính để đếm theo ngày lịch (o1 10:00 ngày 30/1 tới o3 23:00 ngày 1/2 là
  2 ngày).

Trên PostgreSQL, `date_diff` không có; viết `ts::date - (LAG(ts) OVER w)::date` (trừ hai `date`
ra số nguyên ngày).
