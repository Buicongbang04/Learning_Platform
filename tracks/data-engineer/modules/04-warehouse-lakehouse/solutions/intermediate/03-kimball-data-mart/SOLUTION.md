# Lời giải: Data mart Kimball

Xem `mart.sql`. Quy trình 4 bước của Kimball áp vào bài:

1. **Chọn quy trình nghiệp vụ**: bán hàng (đặt đơn).
2. **Khai báo grain**: một dòng cho mỗi `order_item`. Grain chi tiết nhất có thể, vì tổng hợp lên thì dễ, tách xuống
   thì không. Nếu chọn grain "một dòng mỗi đơn" thì mất khả năng phân tích theo sản phẩm.
3. **Chọn dimension**: customer, product, date (có thể thêm seller, geolocation).
4. **Chọn fact**: `price`, `freight_value`, `total_value`, đều là measure *additive* (cộng được theo mọi chiều).

## Các quyết định

- **Surrogate key** (`customer_key`) thay vì natural key (`customer_id`): khoá nhỏ (INTEGER join nhanh hơn chuỗi
  32 ký tự), tách warehouse khỏi thay đổi ở hệ nguồn, và là điều kiện để làm SCD Type 2 (một `customer_id` có nhiều
  phiên bản, mỗi phiên bản một `customer_key`). Ở đây đánh số bằng `ROW_NUMBER`; thực tế khi nạp tăng dần cần sinh
  key ổn định (sequence hoặc hash).
- **Unknown member (key 0)**: fact không bao giờ làm rơi dòng vì dimension thiếu (late-arriving dimension hoặc
  dữ liệu bẩn). Doanh thu vẫn khớp, và BI hiện nhóm "unknown" để người ta thấy và đi sửa nguồn.
  Dùng `INNER JOIN` là lỗi kinh điển: số liệu mart lệch so với nguồn mà không ai biết.
- **dim_date sinh liên tục**, không lấy từ các ngày có đơn: để báo cáo hiện cả ngày doanh thu bằng 0, và để các
  thuộc tính lịch (cuối tuần, quý, ngày lễ) nằm sẵn trong bảng thay vì tính lại trong mọi truy vấn.
  `date_key` dạng `YYYYMMDD` vừa là số nguyên vừa đọc được bằng mắt.
- `order_status` để thẳng trong fact là một **degenerate dimension** (cùng `order_id`), vì không có thuộc tính đi kèm.

## Kiểm tra nên có trong mọi mart

- Số dòng fact = số dòng nguồn ở cùng grain; khoá grain duy nhất.
- Không có khoá ngoại orphan.
- Tổng measure khớp nguồn (reconciliation). Test của bài kiểm tra đúng ba điều này; trong dự án thật thì viết chúng
  bằng dbt tests hoặc Great Expectations.
