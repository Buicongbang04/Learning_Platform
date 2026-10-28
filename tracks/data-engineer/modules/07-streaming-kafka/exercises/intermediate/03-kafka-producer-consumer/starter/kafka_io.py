"""Producer và consumer Kafka cho order events (kafka-python-ng)."""

from __future__ import annotations

import json  # noqa: F401
import time  # noqa: F401

from kafka import KafkaConsumer, KafkaProducer


def encode_key(key: str | None) -> bytes | None:
    # TODO 1: None giữ nguyên None, chuỗi thì encode UTF-8.
    raise NotImplementedError


def encode_value(event: dict) -> bytes:
    # TODO 2: JSON gọn, sort_keys, giữ Unicode, encode UTF-8.
    raise NotImplementedError


def decode_value(data: bytes) -> dict:
    # TODO 3
    raise NotImplementedError


def producer_config() -> dict:
    """Cấu hình producer bền vững: chờ mọi ISR ack, có retry, gom batch nhẹ."""
    # TODO 4: trả về dict tham số cho KafkaProducer: acks, retries (> 0), linger_ms,
    #         max_in_flight_requests_per_connection=1, key_serializer, value_serializer.
    raise NotImplementedError


def consumer_config(group_id: str) -> dict:
    """Cấu hình consumer at-least-once: tự commit sau khi xử lý, group mới đọc từ đầu."""
    # TODO 5: group_id, enable_auto_commit, auto_offset_reset, key_deserializer, value_deserializer.
    raise NotImplementedError


def make_producer(bootstrap: str) -> KafkaProducer:
    return KafkaProducer(bootstrap_servers=bootstrap, **producer_config())


def produce_events(producer: KafkaProducer, topic: str, events: list[dict]) -> list[tuple[int, int]]:
    """Gửi event với key = order_id. Trả về (partition, offset) của từng event theo thứ tự gửi."""
    # TODO 6: send() từng event (bất đồng bộ), flush(), rồi lấy RecordMetadata từ các future.
    raise NotImplementedError


def consume_events(
    bootstrap: str, topic: str, group_id: str, max_records: int, timeout_s: float = 20.0
) -> list[dict]:
    """Đọc tới khi đủ max_records hoặc hết timeout. Commit offset sau mỗi lần poll có dữ liệu.

    Mỗi phần tử: {"partition", "offset", "key", "value"}.
    """
    # TODO 7: tạo KafkaConsumer(topic, bootstrap_servers=..., **consumer_config(group_id)),
    #         vòng poll() tới khi đủ hoặc hết giờ, commit() sau khi đã gom record, luôn close().
    raise NotImplementedError
