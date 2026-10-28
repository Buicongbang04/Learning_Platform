# Lời giải: thiết kế bảng Cassandra theo truy vấn

## Schema

| Bảng | Partition key | Clustering | Lý do |
| --- | --- | --- | --- |
| `order_events_by_order` | `(order_id)` | `event_time DESC, event_type` | Biết `order_id` khi hỏi; mỗi đơn vài chục sự kiện nên partition nhỏ; `event_type` làm hàng duy nhất khi hai sự kiện cùng giờ |
| `orders_by_seller_day` | `(seller_id, order_date)` | `purchased_at DESC, order_id` | Bucket theo ngày để partition của seller lớn không phình vô hạn; `order_id` chống ghi đè khi hai đơn cùng giây |
| `reviews_by_product` | `(product_id)` | `created_at DESC, review_id` | Lấy review mới nhất bằng `LIMIT`, không sort |

Nhớ rằng Cassandra **upsert** mọi `INSERT`: hai hàng cùng primary key thì hàng sau ghi đè hàng trước, không lỗi.
Vì thế primary key phải xác định duy nhất một hàng — nếu chỉ dùng `PRIMARY KEY ((order_id), event_time)`, sự
kiện "shipped" và "invoice" cùng thời điểm sẽ mất một cái, và không ai báo lỗi.

`CLUSTERING ORDER BY` khiến dữ liệu lưu sẵn theo thứ tự giảm dần trên đĩa, nên `LIMIT n` đọc đúng n hàng đầu
của partition. Truy vấn ngược thứ tự vẫn được (`ORDER BY event_time ASC`) nhưng kém hiệu quả hơn một chút.

Đừng chọn `event_type` hay `score` làm partition key: chỉ vài giá trị, nên toàn bộ dữ liệu dồn vào vài partition
khổng lồ (hot partition).

## Biến đổi dữ liệu

`seller_order_rows` là **denormalization**: một đơn nhiều seller sinh nhiều dòng trong bảng Q2, mỗi dòng chỉ
mang phần giá trị của seller đó. Ứng dụng phải ghi cả bảng Q1/Q2/Q3 khi có dữ liệu mới (thường từ một consumer
Kafka); muốn các bảng nhất quán với nhau thì dùng `LOGGED BATCH` (đảm bảo cuối cùng tất cả đều được ghi, không
phải transaction).

## Ghi và đọc

- **Prepared statement**: Cassandra parse câu lệnh một lần, client chỉ gửi tham số; driver còn biết partition
  key nên gửi thẳng tới replica giữ dữ liệu (token-aware routing).
- `Decimal(str(x))` thay vì `Decimal(x)` để tránh lỗi biểu diễn nhị phân của float (`Decimal(99.9)` =
  `99.900000000000005684...`).
- Truy vấn đọc luôn cung cấp **đủ** partition key bằng `=`, không cần `ALLOW FILTERING`.
- Ghi số lượng lớn nên dùng `execute_async` hoặc `cassandra.concurrent.execute_concurrent_with_args` thay vì
  vòng lặp đồng bộ.
