"""Consumer Kafka tính feature cửa sổ tumbling theo event time cho từng zone."""


def consume_windows(bootstrap: str, topic: str, *, window_s: int = 900, lateness_s: int = 180, idle_ms: int = 3000) -> dict:
    raise NotImplementedError(
        "TODO: đọc topic từ đầu bằng KafkaConsumer, gộp cửa sổ theo event time, "
        "trả {'windows', 'late', 'duplicates', 'consumed'}"
    )
