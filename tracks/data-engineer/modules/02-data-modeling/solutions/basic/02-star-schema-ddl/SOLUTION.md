# Lời giải: DDL star schema cho doanh thu theo item

## Cách làm

- **dim_date** sinh hoàn toàn bằng SQL từ `generate_series`. Key `YYYYMMDD` là ngoại lệ hợp lý
  với quy tắc "surrogate key vô nghĩa": ngày không bao giờ đổi, và key đọc được giúp debug, partition
  fact theo `purchase_date_key` dễ dàng. `isodow()` cho thứ Hai = 1, nên cuối tuần là 6 và 7.
- **Dimension** dùng surrogate key nguyên (`customer_key`) và giữ natural key (`customer_id`) làm
  thuộc tính. Ở bài SCD2 sau, cùng một `customer_id` sẽ có nhiều `customer_key`.
- **Fact** chỉ chứa khoá và measure. `order_id` là degenerate dimension: cần để đếm đơn và truy
  vết, nhưng không có thuộc tính nào đáng tách thành bảng riêng. Khoá chính `(order_id,
  order_item_id)` khớp grain và chặn nạp trùng.
- **Khoá ngoại** bảo đảm mọi fact trỏ tới dimension có thật. Trong warehouse lớn (BigQuery,
  Snowflake) FK thường chỉ mang tính khai báo, không được ép; khi đó phải kiểm tra bằng data test
  (dbt `relationships`) và dùng dòng "Unknown" `-1` cho dimension thiếu.

## Truy vấn

Truy vấn phân tích trên star schema luôn có dạng: lọc/nhóm theo thuộc tính dimension, tổng hợp
measure của fact, mỗi dimension chỉ cách fact một join. Đây là lý do star schema dễ dùng cho BI.

## Lưu ý thiết kế

- Không đặt `payment_value` vào fact này: thanh toán ở grain đơn hàng, đặt vào grain item sẽ bị
  nhân bản khi đơn có nhiều item.
- Có thể thêm `delivered_date_key` (role-playing `dim_date`) nếu cần phân tích theo ngày giao.
