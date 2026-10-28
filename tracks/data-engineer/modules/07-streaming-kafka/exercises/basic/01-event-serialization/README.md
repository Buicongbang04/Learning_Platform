---
title: Serialize và validate order event trước khi gửi Kafka
level: basic
services: []
files:
  - path: starter/events.py
    note: 4 TODO
  - path: tests/test_event_serialization.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/basic/01-event-serialization -q
---

## Mục tiêu

Kafka chỉ lưu bytes. Bài này giúp bạn viết lớp serialize/deserialize có validate theo JSON Schema
và chọn key cho record, để producer không đẩy dữ liệu rác làm gãy consumer phía sau.

## Đề bài

Trong `starter/events.py` đã có `ORDER_EVENT_SCHEMA` mô tả một order event của Olist. Hoàn thành:

1. `validate(event) -> list[str]`: trả về danh sách thông báo lỗi theo schema (dùng
   `jsonschema.Draft202012Validator`). Event hợp lệ trả về `[]`.
2. `serialize(event) -> bytes`: event không hợp lệ thì `raise ValueError`. Hợp lệ thì trả về JSON
   gọn (không khoảng trắng thừa), key sắp xếp, giữ nguyên ký tự Unicode (`"são paulo"` không bị
   đổi thành `ã`), mã hoá UTF-8.
3. `deserialize(data) -> dict`: ngược lại của `serialize`. Bytes không phải UTF-8, không phải JSON,
   hoặc JSON không phải object thì `raise ValueError` (consumer sẽ đẩy những message này sang DLQ).
4. `message_key(event) -> bytes`: trả về `order_id` dạng bytes. Thiếu `order_id` thì `raise ValueError`.

## Tiêu chí đạt

- `validate` trả về `[]` cho event hợp lệ và ít nhất một lỗi cho amount âm, status lạ, order_id rỗng, amount kiểu chuỗi, thiếu `event_time`.
- `serialize` trả về bytes JSON gọn, key sắp xếp, giữ Unicode; từ chối event sai bằng `ValueError`.
- `deserialize(serialize(e)) == e`.
- `deserialize` ném `ValueError` với bytes rác, JSON array, bytes không phải UTF-8.
- `message_key` trả về `order_id` dạng bytes.

## Gợi ý

### Gợi ý 1

`Draft202012Validator(schema).iter_errors(event)` sinh ra các lỗi; mỗi lỗi có thuộc tính `.message`.
Tạo validator một lần ở mức module để không compile schema mỗi lần gọi.

### Gợi ý 2

`json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")`.
Khi deserialize, bắt cả `UnicodeDecodeError` và `json.JSONDecodeError` rồi ném lại `ValueError`.
