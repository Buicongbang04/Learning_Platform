---
title: Áp dụng CDC và khôi phục sink sau crash
level: intermediate
services: []
files:
  - path: starter/cdc_sink.py
    note: 1 TODO, hàm initialize đã có sẵn
  - path: tests/test_cdc_sink.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/intermediate/04-cdc-sink -q
---

## Mục tiêu

Hiểu snapshot/create/update/delete/tombstone, áp dụng thay đổi vào bảng đích và lưu checkpoint cùng
transaction. Test chạy không cần Kafka; sau đó dùng cùng code trong [lab CDC thật](../../../cdc-lab.md).

## Đề bài

Hàm initialize đã tạo hai bảng SQLite:

- orders(order_id PK, status, amount_cents): trạng thái hiện tại, tiền ở đơn vị cents.
- checkpoints(topic, partition_id, last_offset): khóa chính (topic, partition_id).

Hoàn thiện apply_record(con, topic, partition, offset, key, value):

1. Nếu offset nhỏ hơn hoặc bằng last_offset đã lưu của đúng topic/partition, không thay đổi gì, trả False.
2. Envelope không bọc schema: key có order_id, value có op và after.
   op r (snapshot), c (create), u (update) dùng upsert toàn bộ dòng after; op d dùng key để DELETE.
   value None là tombstone: không sửa orders, vẫn tiến checkpoint.
3. Dòng after phải khớp order_id trong key, có status thuộc danh sách STATUSES, amount_cents
   là int không âm (bool không được coi là tiền). Dữ liệu sai hoặc op không hỗ trợ raise ValueError.
4. Thay đổi orders và checkpoint chạy trong **cùng transaction**; có lỗi rollback cả hai.
   Offset lưu là offset record vừa xử lý, không phải offset kế tiếp.
5. Record mới xử lý thành công trả True. Không commit Kafka trong hàm này.

Giả định bài: một writer SQLite, record được đưa vào theo thứ tự offset tăng dần của mỗi partition,
khóa không đổi partition và topic không bị tạo lại. Checkpoint không phát hiện thiếu record khi caller
tự bỏ qua một offset; caller phải cung cấp đầy đủ luồng đã đọc. Replay toàn bộ vào bảng mới cần database
và consumer group mới. Không so offset giữa hai partition.

Ví dụ:
key = {"order_id": "o1"}
value = {"op": "u", "after": {"order_id": "o1", "status": "delivered", "amount_cents": 15000}}

Consumer thật gọi apply_record rồi commit **offset kế tiếp** cho đúng Kafka partition.
Crash sau DB commit nhưng trước Kafka commit khiến record tới lại: hàm nhận ra đã xử lý.

## Tiêu chí đạt

- Snapshot, sửa, xóa, tombstone và phát lại đều đúng.
- Event cũ không làm sống lại đơn đã xóa; checkpoint của các partition độc lập.
- Schema sai và lỗi ghi checkpoint đều không để lại thay đổi nửa vời.
- Giải thích được vì sao hai commit ở hai hệ vẫn cần idempotency; test offline không chứng minh broker HA.

## Gợi ý

### Gợi ý 1

BEGIN IMMEDIATE, SELECT checkpoint, validate, upsert/delete, cập nhật checkpoint, COMMIT.
Có exception thì ROLLBACK và raise lại.

### Gợi ý 2

Dùng key để xóa vì after của delete là NULL. Tombstone khác envelope op d:
nó phục vụ log compaction; không phải một dòng đơn hàng để parse.
