"""Serialize / deserialize order event của Olist trước khi gửi lên Kafka."""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

ORDER_EVENT_SCHEMA = {
    "type": "object",
    "required": ["event_id", "order_id", "status", "amount", "event_time"],
    "properties": {
        "event_id": {"type": "string", "minLength": 1},
        "order_id": {"type": "string", "minLength": 1},
        "status": {"enum": ["created", "approved", "shipped", "delivered", "canceled"]},
        "amount": {"type": "number", "minimum": 0},
        "customer_state": {"type": "string", "minLength": 2, "maxLength": 2},
        "event_time": {"type": "string"},
    },
    "additionalProperties": True,
}

_VALIDATOR = Draft202012Validator(ORDER_EVENT_SCHEMA)


def validate(event: dict) -> list[str]:
    """Trả về danh sách lỗi (chuỗi). Rỗng nghĩa là event hợp lệ."""
    errors = sorted(_VALIDATOR.iter_errors(event), key=lambda e: list(e.path))
    return [error.message for error in errors]


def serialize(event: dict) -> bytes:
    """Validate rồi mã hoá event thành JSON UTF-8 gọn, key sắp xếp."""
    errors = validate(event)
    if errors:
        raise ValueError("Event không hợp lệ: " + "; ".join(errors))
    text = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def deserialize(data: bytes) -> dict:
    """Giải mã bytes về dict. Bytes không phải JSON object hợp lệ thì ném ValueError."""
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Không giải mã được message: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Message phải là một JSON object")
    return value


def message_key(event: dict) -> bytes:
    """Key của record Kafka: order_id dạng bytes UTF-8, để mọi event cùng đơn vào cùng partition."""
    order_id = event.get("order_id")
    if not order_id:
        raise ValueError("Event thiếu order_id")
    return str(order_id).encode("utf-8")
