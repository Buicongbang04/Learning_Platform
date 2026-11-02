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


_PRIMITIVES = {int: "integer", float: "number", str: "string", bool: "boolean"}


def schema_for(annotation, where: str = "") -> dict:
    if annotation in _PRIMITIVES:
        return {"type": _PRIMITIVES[annotation]}
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is Literal:
        kinds = {type(v) for v in args}
        if kinds == {str}:
            return {"type": "string", "enum": list(args)}
        if kinds == {int}:
            return {"type": "integer", "enum": list(args)}
        raise TypeError(f"{where}: Literal chỉ nhận toàn str hoặc toàn int")
    if origin is list:
        if len(args) != 1:
            raise TypeError(f"{where}: list cần đúng một kiểu phần tử, ví dụ list[str]")
        return {"type": "array", "items": schema_for(args[0], where)}
    if origin in (typing.Union, types.UnionType):
        inner = [a for a in args if a is not type(None)]
        if len(args) == 2 and len(inner) == 1:
            schema = dict(schema_for(inner[0], where))
            schema["type"] = [schema["type"], "null"]
            if "enum" in schema:
                schema["enum"] = [*schema["enum"], None]
            return schema
        raise TypeError(f"{where}: Union chỉ hỗ trợ dạng `T | None`")
    raise TypeError(f"{where}: kiểu {annotation!r} chưa hỗ trợ")


_ARG = re.compile(r"^\s*(\w+)\s*(?:\([^)]*\))?\s*:\s*(.+)$")


def parse_docstring(doc: str | None) -> tuple[str, dict[str, str]]:
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
    name = fn.__name__
    description, docs = parse_docstring(fn.__doc__)
    hints = typing.get_type_hints(fn)
    properties: dict[str, dict] = {}
    required: list[str] = []
    for pname, param in inspect.signature(fn).parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            raise TypeError(f"{name}: không hỗ trợ *args/**kwargs ({pname})")
        if pname not in hints:
            raise TypeError(f"{name}: tham số {pname} thiếu type hint")
        schema = schema_for(hints[pname], f"{name}.{pname}")
        if pname in docs:
            schema["description"] = docs[pname]
        if param.default is inspect.Parameter.empty:
            required.append(pname)
        elif param.default is not None:
            schema["default"] = param.default
        properties[pname] = schema
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required,
                       "additionalProperties": False}}}


class ToolRegistry:
    def __init__(self):
        self._fns: dict[str, Callable] = {}
        self._specs: dict[str, dict] = {}

    def register(self, fn: Callable) -> Callable:
        spec = tool_spec(fn)
        name = spec["function"]["name"]
        if name in self._fns:
            raise ValueError(f"tool {name!r} đã được đăng ký")
        self._fns[name], self._specs[name] = fn, spec
        return fn

    def specs(self) -> list[dict]:
        return list(self._specs.values())

    def call(self, name: str, arguments) -> Observation:
        if name not in self._fns:
            return Observation(False, f"ERROR: không có tool {name!r}. Tool hợp lệ: {', '.join(self._fns)}.")
        args = arguments
        if isinstance(arguments, str):
            try:
                args = json.loads(arguments)
            except ValueError:
                args = None
        if not isinstance(args, dict):
            return Observation(False, f"ERROR: tham số của {name} phải là một JSON object, nhận {arguments!r}.")
        validator = jsonschema.Draft202012Validator(self._specs[name]["function"]["parameters"])
        errors = sorted(validator.iter_errors(args), key=lambda e: [str(p) for p in e.path])
        if errors:
            detail = "; ".join((".".join(map(str, e.path)) + ": " if e.path else "") + e.message for e in errors)
            return Observation(False, f"ERROR: tham số của {name} sai: {detail}")
        try:
            result = self._fns[name](**args)
        except Exception as exc:
            return Observation(False, f"ERROR: {name} lỗi khi chạy: {type(exc).__name__}: {exc}")
        if isinstance(result, str):
            return Observation(True, result)
        return Observation(True, json.dumps(result, ensure_ascii=False, default=str))
