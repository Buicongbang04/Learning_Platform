"""Tool registry cho agent: JSON Schema sinh từ chữ ký hàm, kiểm tham số, lỗi thành Observation."""

import inspect
import json
import re
import types
import typing
from dataclasses import dataclass
from typing import Callable, Literal

import jsonschema


@dataclass
class Observation:
    ok: bool
    content: str


def schema_for(annotation, where: str = "") -> dict:
    """JSON Schema của một type hint.

    int, float, str, bool -> {"type": "integer" | "number" | "string" | "boolean"}
    list[T]               -> {"type": "array", "items": schema_for(T)}
    Literal["a", "b"]     -> {"type": "string", "enum": ["a", "b"]}   (toàn int thì "integer")
    T | None (Optional[T])-> schema_for(T) với "type" thành [<type của T>, "null"], có enum thì thêm None vào enum
    Kiểu khác (dict, tuple, Union nhiều nhánh, Literal lẫn kiểu, class tự định nghĩa...) -> TypeError có nêu `where`.
    """
    # TODO
    raise NotImplementedError


_ARG = re.compile(r"^\s*(\w+)\s*(?:\([^)]*\))?\s*:\s*(.+)$")


def parse_docstring(doc: str | None) -> tuple[str, dict[str, str]]:
    """(mô tả, {tên tham số: mô tả}) từ docstring kiểu Google: đoạn trước `Args:` là mô tả hàm."""
    doc = inspect.cleandoc(doc or "")
    head, _, rest = doc.partition("Args:")
    description = " ".join(line.strip() for line in head.splitlines() if line.strip())
    params: dict[str, str] = {}
    current = None
    for line in rest.splitlines():
        if not line.strip():
            continue
        if not line[0].isspace() and line.rstrip().endswith(":"):
            break
        match = _ARG.match(line)
        if match:
            current = match.group(1)
            params[current] = match.group(2).strip()
        elif current:
            params[current] += " " + line.strip()
    return description, params


def tool_spec(fn: Callable) -> dict:
    """Spec dạng OpenAI {"type": "function", "function": {"name", "description", "parameters"}} từ chữ ký hàm.

    - name: fn.__name__; description và mô tả từng tham số: parse_docstring(fn.__doc__).
    - parameters: {"type": "object", "properties": {...}, "required": [...], "additionalProperties": False};
      properties theo đúng thứ tự tham số; tham số có mô tả trong Args thì thêm "description".
    - Tham số không có giá trị mặc định là required; có mặc định khác None thì thêm "default".
    - Tham số thiếu type hint, *args hoặc **kwargs -> TypeError.
    """
    # TODO
    raise NotImplementedError


class ToolRegistry:
    """Đăng ký hàm Python làm tool; gọi tool bằng tên và tham số do model sinh ra, không bao giờ ném lỗi."""

    def __init__(self):
        self._fns: dict[str, Callable] = {}
        self._specs: dict[str, dict] = {}

    def register(self, fn: Callable) -> Callable:
        """Đăng ký fn (dùng được như decorator, trả lại chính fn). Trùng tên -> ValueError."""
        # TODO
        raise NotImplementedError

    def specs(self) -> list[dict]:
        """Spec của mọi tool, theo thứ tự đăng ký."""
        # TODO
        raise NotImplementedError

    def call(self, name: str, arguments) -> Observation:
        """Gọi tool. arguments là dict hoặc chuỗi JSON.

        Thành công: Observation(True, kết quả) với kết quả là chuỗi giữ nguyên, kiểu khác thì
        json.dumps(..., ensure_ascii=False). Mọi lỗi -> Observation(False, "ERROR: ...") đủ để model tự sửa:
        tool không tồn tại (kèm danh sách tool hợp lệ), arguments không phải JSON object, tham số sai schema
        (kèm thông điệp của jsonschema), hàm ném exception (kèm tên lớp và thông điệp exception).
        """
        # TODO
        raise NotImplementedError
