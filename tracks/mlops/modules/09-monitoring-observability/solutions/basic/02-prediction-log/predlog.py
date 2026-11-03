import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

ALLOWED_FEATURES = ("trip_distance_km", "pickup_zone", "dropoff_zone", "hour")


def log_prediction(stream, *, request_id: str, model_version: str, features: dict, prediction: float,
                   fallback: bool, ts: datetime) -> None:
    if ts.tzinfo is None:
        raise ValueError("ts phải có múi giờ")
    if not math.isfinite(prediction):
        raise ValueError("prediction phải hữu hạn")
    record = {
        "ts": ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "request_id": request_id,
        "model_version": model_version,
        "prediction": prediction,
        "fallback": bool(fallback),
        "features": {key: features[key] for key in ALLOWED_FEATURES if key in features},
    }
    stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


@dataclass
class JoinResult:
    rows: list[dict] = field(default_factory=list)
    unmatched_predictions: int = 0
    orphan_labels: int = 0
    bad_lines: int = 0
    bad_labels: int = 0


def _parse(line: str) -> dict | None:
    try:
        record = json.loads(line)
    except ValueError:
        return None
    if not isinstance(record, dict) or not isinstance(record.get("request_id"), str):
        return None
    if not isinstance(record.get("ts"), str):
        return None
    prediction = record.get("prediction")
    if isinstance(prediction, bool) or not isinstance(prediction, (int, float)) or not math.isfinite(prediction):
        return None
    return record


def join_labels(lines, labels) -> JoinResult:
    result = JoinResult()
    predictions: dict[str, dict] = {}
    for line in lines:
        if not line.strip():
            continue
        record = _parse(line)
        if record is None:
            result.bad_lines += 1
            continue
        kept = predictions.get(record["request_id"])
        if kept is None or record["ts"] >= kept["ts"]:
            predictions[record["request_id"]] = record
    actuals: dict[str, float] = {}
    for label in labels:
        actual = label.get("actual_seconds")
        request_id = label.get("request_id")
        if (not isinstance(request_id, str) or isinstance(actual, bool)
                or not isinstance(actual, (int, float)) or not math.isfinite(actual)):
            result.bad_labels += 1
            continue
        actuals[request_id] = float(actual)
    for request_id, record in predictions.items():
        if request_id not in actuals:
            result.unmatched_predictions += 1
            continue
        result.rows.append({
            "request_id": request_id,
            "ts": record["ts"],
            "model_version": record.get("model_version"),
            "prediction": float(record["prediction"]),
            "actual_seconds": actuals[request_id],
            "abs_error": abs(float(record["prediction"]) - actuals[request_id]),
        })
    result.orphan_labels = sum(1 for request_id in actuals if request_id not in predictions)
    result.rows.sort(key=lambda row: (row["ts"], row["request_id"]))
    return result
