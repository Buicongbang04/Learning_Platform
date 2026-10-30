# Lời giải: đọc SQL đoán kết quả và chọn công cụ

## Đoán kết quả

- **count-null (d) `5, 3, 2`**: `count(*)` đếm dòng; `count(col)` bỏ NULL; `count(DISTINCT col)` bỏ NULL rồi bỏ
  trùng. Trên Online Retail II: 1 044 848 dòng, `count(customer_id)` 809 561, 5 942 khách khác nhau. Báo "số
  khách" bằng `count(*)` là đếm dòng hoá đơn.
- **avg-null (a) `15 và 7.5`**: `avg` bỏ NULL nên chia cho 2. Câu hỏi business quyết định cái nào đúng: "giảm giá
  trung bình của đơn **có** giảm giá" là 15; "giảm giá trung bình mỗi đơn" là 7.5 (đơn không giảm giá là 0). NULL
  ở đây nghĩa là 0 hay "không biết"? Hỏi trước khi `coalesce`.
- **left-join-where (c)**: điều kiện trên bảng bên phải đặt trong `WHERE` loại mọi dòng mà `o.status` là NULL,
  tức mọi khách không có đơn: `LEFT JOIN` thành `INNER JOIN`. Muốn giữ mọi khách: đưa điều kiện vào `ON` (`LEFT
  JOIN orders o ON o.customer_id = c.id AND o.status = 'delivered'`) và đếm `count(DISTINCT o.customer_id)` cho số
  khách có đơn delivered.
- **not-equal-null (b) `1`**: `NULL <> 'UK'` là NULL, không phải TRUE. Chỉ 'France' qua được. Muốn tính cả dòng
  NULL: `WHERE country IS DISTINCT FROM 'UK'` hoặc `coalesce(country, '') <> 'UK'`.
- **fanout-sum (c) `18`**: phí đơn A (5) lặp 3 lần theo 3 dòng item, cộng phí B (3): 15 + 3 = 18. Cột ở grain
  **đơn** không được cộng sau khi join xuống grain **dòng item**. Sửa: tổng phí từ `orders` riêng, hoặc gom
  `order_items` về grain đơn trước khi join.
- **timestamp-between (a)**: chuỗi `'2011-11-30'` được ép thành `2011-11-30 00:00:00`, nên 14:00 nằm ngoài. Dùng
  khoảng nửa mở `ts >= '2011-11-01' AND ts < '2011-12-01'`.

## Chọn công cụ

- **tool-csv-laptop (d) DuckDB**: đọc thẳng CSV/Parquet bằng SQL, không cần dựng server, xử lý vài GB trên laptop
  trong vài giây. Excel giới hạn 1 048 576 dòng mỗi sheet; Postgres trên Docker được nhưng tốn công nạp và
  khai báo schema cho một việc một lần; Spark thừa với 2 GB.
- **tool-prod-db (b) BigQuery**: truy vấn quét 2 năm dữ liệu trên database production tranh tài nguyên với ứng
  dụng (khách đặt hàng chậm đi) và thường bị cấm. Báo cáo theo ngày không cần dữ liệu tới từng phút; trễ một đêm
  chấp nhận được. Nếu thật sự cần gần thời gian thực thì hỏi team data về read replica, đừng tự chạy lên primary.
- **tool-recurring (a) model + dashboard**: câu hỏi lặp lại, nhiều người dùng: đưa logic vào một chỗ (view/model
  dbt trong warehouse) để mọi người dùng chung **một định nghĩa**, rồi dựng dashboard (module 09, 10). Gửi tệp
  `.sql` cho từng người dẫn tới năm phiên bản sửa khác nhau; dán email hay chép vào Sheets không tái lập được và dễ lệch số.
- **tool-sql-vs-pandas (c)**: tổng hợp ở nơi dữ liệu nằm (warehouse mạnh về quét và gom nhóm song song), chỉ kéo
  về bảng đã thu nhỏ (vài trăm dòng theo tuần) để làm những việc SQL không giỏi: chart, kiểm định, mô hình. Kéo
  500 triệu dòng về laptop thì hết bộ nhớ và tốn phí egress.

## Quy tắc rút ra

1. Mọi so sánh với NULL là NULL; `WHERE` chỉ giữ TRUE. Kiểm NULL bằng `IS NULL`, `IS DISTINCT FROM`.
2. Điều kiện của bảng bên phải `LEFT JOIN` đặt trong `ON`, không trong `WHERE`.
3. Biết grain của mỗi cột trước khi `SUM` sau join.
4. Khoảng thời gian: nửa mở `>= đầu AND < sau cuối`.
5. Chạy SQL ở nơi dữ liệu nằm; không chạy phân tích nặng lên database production.
