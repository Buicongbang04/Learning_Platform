import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

ALLOWED_FEATURES = ("trip_distance_km", "pickup_zone", "dropoff_zone", "hour")


def log_prediction(stream, *, request_id: str, model_version: str, features: dict, prediction: float,
                   fallback: bool, ts: datetime) -> None:
    """Ghi đúng một dòng JSON vào `stream` (xem đề bài về khoá, múi giờ, lọc feature, giá trị không hợp lệ)."""
    # TODO


@dataclass
class JoinResult:
    rows: list[dict] = field(default_factory=list)
    unmatched_predictions: int = 0
    orphan_labels: int = 0
    bad_lines: int = 0
    bad_labels: int = 0


def join_labels(lines, labels) -> JoinResult:
    """Nối các dòng log dự đoán với nhãn thật theo `request_id` (xem đề bài về các ca biên)."""
    # TODO
    return JoinResult()
