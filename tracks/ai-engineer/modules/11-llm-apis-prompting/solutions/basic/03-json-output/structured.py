"""Structured output phía client: tách JSON khỏi câu trả lời, kiểm theo JSON Schema (tập con), gọi lại khi sai.

Chỉ dùng thư viện chuẩn (và `llmkit` cho kiểu LLM). Tập con JSON Schema được hỗ trợ: type, enum, required,
properties, additionalProperties (false), items, minimum, maximum, minLength, maxLength, minItems, maxItems.
"""

from __future__ import annotations

import json

TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class ExtractionError(RuntimeError):
    def __init__(self, message: str, attempts: list[dict]):
        super().__init__(message)
        self.attempts = attempts


def extract_json(text: str):
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                value, _ = decoder.raw_decode(text, i)
            except ValueError:
                continue
            return value
    raise ValueError("không tìm thấy JSON object hoặc array trong câu trả lời")


def validate(instance, schema: dict, path: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        if not any(TYPES[t](instance) for t in allowed):
            return [f"{path}: cần kiểu {'|'.join(allowed)}, nhận {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} không thuộc enum {schema['enum']}")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: thiếu khoá bắt buộc {key!r}")
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: khoá không được phép {key!r}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: cần ít nhất {schema['minItems']} phần tử")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: nhiều nhất {schema['maxItems']} phần tử")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += validate(item, schema["items"], f"{path}[{i}]")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: chuỗi ngắn hơn {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: chuỗi dài hơn {schema['maxLength']}")
    if TYPES["number"](instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: nhỏ hơn minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: lớn hơn maximum {schema['maximum']}")
    return errors


def generate_validated(llm, messages: list[dict], schema: dict, *, max_retries: int = 2) -> dict:
    history = list(messages)
    attempts: list[dict] = []
    for _ in range(max_retries + 1):
        reply = llm.chat(history, json_schema=schema)
        try:
            value = extract_json(reply)
            errors = validate(value, schema)
        except ValueError as exc:
            errors = [str(exc)]
        attempts.append({"reply": reply, "errors": errors})
        if not errors:
            return value
        feedback = ("JSON chưa hợp lệ theo schema:\n" + "\n".join(f"- {e}" for e in errors)
                    + "\nTrả lời lại CHỈ bằng JSON đúng schema.")
        history = history + [{"role": "assistant", "content": reply}, {"role": "user", "content": feedback}]
    raise ExtractionError(f"không có JSON hợp lệ sau {len(attempts)} lần gọi", attempts)
