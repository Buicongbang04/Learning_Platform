---
title: Producer và consumer Kafka thật cho order events
level: intermediate
services: [kafka]
files:
  - path: starter/kafka_io.py
    note: 7 TODO
  - path: tests/test_kafka_producer_consumer.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml up -d kafka
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/intermediate/03-kafka-producer-consumer -q
---

## Mục tiêu

Viết producer bền vững (`acks=all`, retry, giữ thứ tự) và consumer at-least-once (commit thủ công
sau khi xử lý) bằng `kafka-python-ng`, rồi tự kiểm chứng: cùng key thì cùng partition, đọc lại theo
group, group mới thì replay từ đầu.

## Đề bài

Hoàn thành `starter/kafka_io.py`:

1. `encode_key`, `encode_value`, `decode_value`: chuỗi ↔ bytes UTF-8; value là JSON gọn,
   `sort_keys`, giữ Unicode.
2. `producer_config()`: dict tham số cho `KafkaProducer` gồm `acks="all"`, `retries` > 0,
   `linger_ms`, `max_in_flight_requests_per_connection=1`, `key_serializer`, `value_serializer`.
3. `consumer_config(group_id)`: dict tham số cho `KafkaConsumer` gồm `group_id`,
   `enable_auto_commit=False`, `auto_offset_reset="earliest"`, `key_deserializer` (bytes → str,
   giữ `None`), `value_deserializer`.
4. `produce_events(producer, topic, events)`: gửi mỗi event với key `order_id`, `flush()`, rồi trả về
   list `(partition, offset)` theo đúng thứ tự gửi.
5. `consume_events(bootstrap, topic, group_id, max_records, timeout_s=20)`: poll tới khi đủ
   `max_records` hoặc hết thời gian, `commit()` sau mỗi lần poll có dữ liệu, luôn `close()`. Trả về
   list `{"partition", "offset", "key", "value"}`.

`make_producer` đã viết sẵn. Bốn test đầu chạy offline; ba test sau cần Kafka (tự skip nếu chưa bật,
cổng host `9094`, đọc từ `testkit.KAFKA_BOOTSTRAP`). Test tự tạo topic 3 partition tên ngẫu nhiên và
xoá khi xong.

## Tiêu chí đạt

- Test offline pass: serializer đúng, cấu hình producer bền vững, consumer không auto commit.
- Có Kafka: mọi event của một `order_id` nằm ở cùng partition, offset tăng dần.
- Consumer đọc đủ 9 event, trạng thái mỗi đơn theo đúng thứ tự `created → approved → shipped`.
- Cùng group đọc lại không nhận gì (đã commit); group mới đọc lại đủ 9 event (replay).

## Gợi ý

### Gợi ý 1

`producer.send(topic, key=..., value=...)` trả về future; gom hết future, gọi `producer.flush()`
một lần, rồi `future.get(timeout=10)` để lấy `RecordMetadata` có `.partition` và `.offset`. Gọi
`.get()` ngay sau từng `send` cũng đúng nhưng mất lợi ích batching.

### Gợi ý 2

`consumer.poll(timeout_ms=500)` trả về dict `TopicPartition -> list[ConsumerRecord]`. Lần poll đầu
của group mới thường rỗng vì đang join group và nhận partition, nên phải lặp tới deadline
(`time.monotonic()`). Đặt `consumer.close()` trong `finally`.
