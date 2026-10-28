# Lời giải: Serialize và validate order event

## Cách làm

- Tạo `Draft202012Validator(ORDER_EVENT_SCHEMA)` một lần ở mức module. `validate` gom
  `error.message` từ `iter_errors`, sắp theo `error.path` cho kết quả ổn định.
- `serialize` validate trước, rồi `json.dumps(..., ensure_ascii=False, sort_keys=True,
  separators=(",", ":"))` và `.encode("utf-8")`.
- `deserialize` bắt `UnicodeDecodeError`, `json.JSONDecodeError` và kiểm tra kết quả là `dict`,
  mọi trường hợp sai đều thành `ValueError` để consumer xử lý thống nhất (đẩy sang DLQ).
- `message_key` trả `order_id.encode("utf-8")`.

## Vì sao

- **Validate ở producer** chặn dữ liệu sai ngay tại nguồn. Một event `amount="129.9"` lọt vào
  topic sẽ làm hỏng mọi consumer, và vì Kafka giữ dữ liệu theo retention nên không "xoá" được.
- **Key sắp xếp và JSON gọn** cho bytes ổn định (cùng event luôn ra cùng bytes), tiết kiệm băng
  thông, tiện so sánh, hash, dedup. `ensure_ascii=False` giữ tên thành phố tiếng Bồ Đào Nha dễ đọc
  và gọn hơn `ã`.
- **Key = order_id** để mọi event của một đơn vào cùng partition, giữ thứ tự trạng thái.
- Trong production nên dùng Schema Registry (Avro/Protobuf/JSON Schema) để quản lý version schema
  thay vì nhúng schema trong code.
