"""Producer và consumer Kafka cho order events (kafka-python-ng)."""

from __future__ import annotations

import json
import time

from kafka import KafkaConsumer, KafkaProducer


def encode_key(key: str | None) -> bytes | None:
    return None if key is None else key.encode("utf-8")


def encode_value(event: dict) -> bytes:
    return json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def decode_value(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))


def producer_config() -> dict:
    """Cấu hình producer bền vững: chờ mọi ISR ack, có retry, gom batch nhẹ."""
    return {
        "acks": "all",
        "retries": 5,
        "linger_ms": 10,
        "max_in_flight_requests_per_connection": 1,  # retry không đảo thứ tự
        "key_serializer": encode_key,
        "value_serializer": encode_value,
    }


def consumer_config(group_id: str) -> dict:
    """Cấu hình consumer at-least-once: tự commit sau khi xử lý, group mới đọc từ đầu."""
    return {
        "group_id": group_id,
        "enable_auto_commit": False,
        "auto_offset_reset": "earliest",
        "key_deserializer": lambda b: None if b is None else b.decode("utf-8"),
        "value_deserializer": decode_value,
    }


def make_producer(bootstrap: str) -> KafkaProducer:
    return KafkaProducer(bootstrap_servers=bootstrap, **producer_config())


def produce_events(producer: KafkaProducer, topic: str, events: list[dict]) -> list[tuple[int, int]]:
    """Gửi event với key = order_id. Trả về (partition, offset) của từng event theo thứ tự gửi."""
    futures = [producer.send(topic, key=e["order_id"], value=e) for e in events]
    producer.flush()
    positions = []
    for future in futures:
        meta = future.get(timeout=10)
        positions.append((meta.partition, meta.offset))
    return positions


def consume_events(
    bootstrap: str, topic: str, group_id: str, max_records: int, timeout_s: float = 20.0
) -> list[dict]:
    """Đọc tới khi đủ max_records hoặc hết timeout. Commit offset sau mỗi lần poll có dữ liệu.

    Mỗi phần tử: {"partition", "offset", "key", "value"}.
    """
    consumer = KafkaConsumer(topic, bootstrap_servers=bootstrap, **consumer_config(group_id))
    out: list[dict] = []
    deadline = time.monotonic() + timeout_s
    try:
        while len(out) < max_records and time.monotonic() < deadline:
            batch = consumer.poll(timeout_ms=500, max_records=max_records - len(out))
            got = False
            for records in batch.values():
                for record in records:
                    out.append(
                        {"partition": record.partition, "offset": record.offset,
                         "key": record.key, "value": record.value}
                    )
                    got = True
            if got:
                consumer.commit()  # "xử lý" xong mới commit: at-least-once
    finally:
        consumer.close()
    return out
