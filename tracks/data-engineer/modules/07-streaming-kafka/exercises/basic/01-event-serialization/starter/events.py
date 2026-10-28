"""Serialize / deserialize order event của Olist trước khi gửi lên Kafka."""

from __future__ import annotations

import json  # noqa: F401  (bạn sẽ cần)

from jsonschema import Draft202012Validator  # noqa: F401  (bạn sẽ cần)

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


def validate(event: dict) -> list[str]:
    """Trả về danh sách lỗi (chuỗi). Rỗng nghĩa là event hợp lệ."""
    # TODO 1: validate event theo ORDER_EVENT_SCHEMA, trả về list message lỗi.
    raise NotImplementedError


def serialize(event: dict) -> bytes:
    """Validate rồi mã hoá event thành JSON UTF-8 gọn, key sắp xếp."""
    # TODO 2: event không hợp lệ thì raise ValueError.
    #         Hợp lệ thì json.dumps(sort_keys, separators gọn, giữ ký tự Unicode) rồi encode UTF-8.
    raise NotImplementedError


def deserialize(data: bytes) -> dict:
    """Giải mã bytes về dict. Bytes không phải JSON object hợp lệ thì ném ValueError."""
    # TODO 3: decode UTF-8, json.loads, kiểm tra là dict. Mọi lỗi đổi thành ValueError.
    raise NotImplementedError


def message_key(event: dict) -> bytes:
    """Key của record Kafka: order_id dạng bytes UTF-8, để mọi event cùng đơn vào cùng partition."""
    # TODO 4: trả về order_id dạng bytes; thiếu order_id thì raise ValueError.
    raise NotImplementedError
