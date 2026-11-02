"""Structured output phía client: tách JSON khỏi câu trả lời, kiểm theo JSON Schema (tập con), gọi lại khi sai.

Chỉ dùng thư viện chuẩn (và `llmkit` cho kiểu LLM). Tập con JSON Schema được hỗ trợ: type, enum, required,
properties, additionalProperties (false), items, minimum, maximum, minLength, maxLength, minItems, maxItems.
Đọc README của bài cho quy ước đường dẫn lỗi.
"""

from __future__ import annotations

import json


class ExtractionError(RuntimeError):
    """Hết lượt gọi mà chưa có JSON hợp lệ. `attempts`: [{"reply": str, "errors": list[str]}, ...]."""

    def __init__(self, message: str, attempts: list[dict]):
        super().__init__(message)
        self.attempts = attempts


def extract_json(text: str):
    """JSON object hoặc array ĐẦU TIÊN parse được trong `text` (có thể nằm trong ```json ... ``` hay giữa văn xuôi).
    ValueError nếu không có."""
    # TODO
    raise NotImplementedError


def validate(instance, schema: dict, path: str = "$") -> list[str]:
    """Danh sách lỗi (rỗng nếu hợp lệ). Mỗi lỗi bắt đầu bằng đường dẫn rồi dấu hai chấm, ví dụ
    "$.aspects[1]: chuỗi ngắn hơn 1". Lỗi thiếu khoá hay thừa khoá gắn với đường dẫn của object chứa nó."""
    # TODO
    raise NotImplementedError


def generate_validated(llm, messages: list[dict], schema: dict, *, max_retries: int = 2):
    """Gọi `llm.chat(messages, json_schema=schema)`, tách và kiểm JSON; sai thì gọi lại tối đa `max_retries` lần,
    mỗi lần thêm câu trả lời sai (assistant) và một message user liệt kê lỗi vào lịch sử. Trả giá trị hợp lệ, hoặc
    ném ExtractionError kèm mọi lần thử. Không sửa `messages` đầu vào."""
    # TODO
    raise NotImplementedError
