# Lời giải: Định nghĩa metric bằng SQL view trên DuckDB

Xem `metrics.sql` cùng thư mục.

## Cách làm

1. **`fct_order_items` là nền chung.** Mọi quy tắc nghiệp vụ "đơn nào được tính" (bỏ `canceled`, `unavailable`)
   nằm ở đúng một chỗ. Các view metric phía sau chỉ aggregate, không lọc lại trạng thái. Đổi quy tắc thì đổi một
   view, mọi metric cập nhật theo.
2. **Ratio tính ở đúng grain.** `aov = SUM(price) / COUNT(DISTINCT order_id)` trong cùng `GROUP BY`. Không lấy
   `AVG(aov)` từ view ngày để ra AOV của state: đó là trung bình của trung bình, sai khi số đơn mỗi ngày khác nhau.
3. **`revenue_share`** dùng window `SUM(revenue) OVER ()` sau khi đã group theo state. Window chạy sau
   `GROUP BY`, nên mẫu số là tổng revenue mọi state.
4. **Late rate ở grain đơn hàng.** Metric này không cần `order_items`. Nếu join vào, đơn `o3` có 2 item sẽ thành
   2 dòng, `COUNT(*)` ra 3 cho RJ. Đây là **fan-out**: luôn chọn bảng ở đúng grain của metric, hoặc dùng
   `COUNT(DISTINCT order_id)` nếu bắt buộc phải join.

## Vì sao làm bằng view

View không tốn lưu trữ và luôn mới, hợp khi dữ liệu nhỏ và logic nhẹ. Khi dữ liệu lớn, các view metric này là
ứng viên để chuyển thành bảng aggregate (bài basic/02) hoặc materialized view, giữ nguyên tên cột để dashboard
không phải sửa.

## Mở rộng

- Thêm `metric_monthly_revenue` dùng `DATE_TRUNC('month', order_date)`.
- Định nghĩa các metric này trong dbt (model + semantic model của MetricFlow) để có test và tài liệu đi kèm.
