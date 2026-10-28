# Lời giải: Producer và consumer Kafka thật

## Cách làm

- Serializer là hàm thuần, tách khỏi Kafka nên test offline được.
- `producer_config()` trả dict, `make_producer` chỉ việc `KafkaProducer(bootstrap_servers=..., **cfg)`.
  Tách cấu hình ra hàm riêng giúp kiểm tra và tái dùng (vd. thêm `security_protocol` theo môi trường).
- `produce_events` gửi bất đồng bộ cả loạt, `flush()` một lần, sau đó mới đọc metadata từ future.
- `consume_events` lặp `poll()` tới khi đủ hoặc hết hạn; sau mỗi lần poll có dữ liệu thì `commit()`;
  `close()` trong `finally` để rời group sạch sẽ (tránh group phải chờ `session.timeout.ms`).

## Vì sao

- **`acks="all"` + retries**: không mất dữ liệu khi leader đổi. Kèm
  `max_in_flight_requests_per_connection=1` để retry không đảo thứ tự (client Java dùng
  `enable.idempotence=true` thay thế, cho phép tới 5 request in-flight mà vẫn giữ thứ tự).
- **Key = `order_id`**: test kiểm tra mọi event của một đơn cùng partition và offset tăng dần, nên
  consumer thấy đúng thứ tự trạng thái.
- **`enable_auto_commit=False`**: auto commit chạy định kỳ theo thời gian, có thể commit trước khi
  bạn xử lý xong (mất dữ liệu khi crash) hoặc sau khi đã xử lý (trùng). Commit thủ công sau khi xử lý
  cho at-least-once rõ ràng. Ở đây "xử lý" là gom vào list; trong thực tế là ghi sink thành công.
- **Replay**: offset thuộc về group, không thuộc về message. Group mới với
  `auto_offset_reset="earliest"` đọc lại toàn bộ dữ liệu còn trong retention. Đây là khác biệt cốt
  lõi so với queue: RabbitMQ/SQS đã xoá message sau khi ack.
- Commit đồng bộ sau mỗi poll đơn giản nhưng thêm độ trễ; consumer throughput cao thường
  `commit_async()` định kỳ và `commit()` đồng bộ khi bị thu hồi partition hoặc khi tắt.
