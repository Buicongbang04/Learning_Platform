# M07: Order events thời gian thực qua Kafka

## Mục tiêu

Xây luồng streaming: event đơn hàng đi vào Kafka, consumer xử lý **event trùng** và **event đến
trễ**, cập nhật bảng trạng thái đơn gần thời gian thực trong Postgres và ghi event thô vào lake.

## Việc cần làm

1. Bật Kafka và tạo topic 3 partition:

   ```bash
   docker compose -f setup/docker-compose.yml up -d kafka postgres
   docker compose -f setup/docker-compose.yml exec kafka /opt/kafka/bin/kafka-topics.sh \
     --bootstrap-server localhost:9092 --create --topic olist.order-events --partitions 3 --replication-factor 1
   ```

2. Chạy producer giả lập (key = `order_id` để mọi event của một đơn vào cùng partition). `--orders-csv data/raw`
   lấy `order_id`/`customer_id` từ Olist thật, nên event join được với `raw`/`dw` đã nạp ở M01–M02; luồng event
   vẫn là giả lập (Olist không công bố event), ghi rõ điều này trong README:

   ```bash
   uv run python data/simulate_events.py --kafka --bootstrap localhost:9094 --topic olist.order-events --rate 20 --dup-rate 0.05 --late-rate 0.05 --orders-csv data/raw
   ```

   Xem trước dữ liệu: `uv run python data/simulate_events.py --count 20 --stdout --orders-csv data/raw`.
3. Viết consumer `project/streaming/order_status_consumer.py` (`kafka-python-ng`):
   - `group_id="order-status"`, `enable_auto_commit=False`, commit offset **sau khi** ghi DB
     thành công (at-least-once).
   - **Dedup**: bảng `stream.processed_events(event_id primary key)`; insert trong cùng transaction
     với cập nhật trạng thái → hiệu quả exactly-once ở phía sink.
   - **Late event**: bảng `stream.order_status_live(order_id, status, last_event_time, updated_at)`;
     chỉ cập nhật khi `event_time` mới hơn `last_event_time` (không để `shipped` đến trễ đè lên `delivered`).
   - Đếm event mỗi loại theo cửa sổ 1 phút (tumbling window) ghi vào `stream.event_counts_1m`;
     chấp nhận trễ tối đa 2 phút (watermark), event trễ hơn thì ghi vào `stream.late_events`.
   - Batch micro: ghi bronze JSONL vào `s3://olist/bronze/order_events/date=YYYY-MM-DD/` mỗi 1000 event (tuỳ chọn).
4. Test logic thuần trong `project/tests/test_streaming.py` với danh sách event đọc từ tệp JSONL:
   `uv run python data/simulate_events.py --count 500 --out tracks/data-engineer/capstone/project/tests/fixtures/events.jsonl`.
5. Thử sự cố: dừng consumer giữa chừng (Ctrl+C), chạy lại; kiểm tra không mất và không đếm trùng.
   Chạy 2 instance consumer cùng group, xem phân chia partition:

   ```bash
   docker compose -f setup/docker-compose.yml exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
     --bootstrap-server localhost:9092 --describe --group order-status
   ```

## Kết quả nộp

- `project/streaming/order_status_consumer.py`, DDL `project/streaming/schema.sql`
- `project/tests/test_streaming.py` + fixture
- Mục "Streaming" trong README: delivery semantics bạn đạt được và vì sao, cách xử lý trùng/trễ,
  sơ đồ mermaid luồng event.

## Tiêu chí đạt

- [ ] Gửi 10.000 event (có 5% trùng): số dòng `processed_events` = số `event_id` duy nhất.
- [ ] Không đơn nào có trạng thái lùi về trước do event trễ.
- [ ] Kill và khởi động lại consumer không làm mất hay đếm trùng event.
- [ ] 2 consumer cùng group chia nhau 3 partition.
- [ ] Consumer lag về 0 sau khi producer dừng.
- [ ] Test streaming chạy pass không cần Kafka.
