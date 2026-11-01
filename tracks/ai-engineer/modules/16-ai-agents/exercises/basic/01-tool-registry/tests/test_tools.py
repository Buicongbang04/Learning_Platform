import json
from typing import Literal, Optional

import jsonschema
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def t():
    return ex.module("tools.py")


def search_books(query: str, limit: int = 5, category: Literal["văn học", "thiếu nhi"] | None = None,
                 in_stock: bool = True, author: str | None = None) -> list[dict]:
    """Tìm sách theo tên hoặc tác giả.

    Trả tối đa `limit` cuốn.

    Args:
        query: một phần tên sách hoặc tên tác giả
        limit (int): số kết quả tối đa,
            từ 1 tới 20
        category: lọc theo thể loại

    Returns:
        danh sách sách
    """
    return [{"query": query, "limit": limit, "category": category}]


# ---------- schema_for ----------


def test_schema_primitives(t):
    assert t.schema_for(int) == {"type": "integer"}
    assert t.schema_for(float) == {"type": "number"}
    assert t.schema_for(str) == {"type": "string"}
    assert t.schema_for(bool) == {"type": "boolean"}


def test_schema_list_and_literal(t):
    assert t.schema_for(list[str]) == {"type": "array", "items": {"type": "string"}}
    assert t.schema_for(list[list[int]]) == {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}}
    assert t.schema_for(Literal["USD", "EUR"]) == {"type": "string", "enum": ["USD", "EUR"]}
    assert t.schema_for(Literal[1, 2, 3]) == {"type": "integer", "enum": [1, 2, 3]}


def test_schema_optional_allows_null(t):
    assert t.schema_for(str | None) == {"type": ["string", "null"]}
    assert t.schema_for(Optional[int]) == {"type": ["integer", "null"]}
    assert t.schema_for(Literal["a", "b"] | None) == {"type": ["string", "null"], "enum": ["a", "b", None]}


@pytest.mark.parametrize("bad", [dict, tuple[int, int], int | str, Literal["a", 1], set[str], object])
def test_schema_unsupported_raises(t, bad):
    with pytest.raises(TypeError):
        t.schema_for(bad, "f.x")


# ---------- tool_spec ----------


def test_tool_spec_shape(t):
    spec = t.tool_spec(search_books)
    assert spec["type"] == "function"
    f = spec["function"]
    assert f["name"] == "search_books"
    assert f["description"] == "Tìm sách theo tên hoặc tác giả. Trả tối đa `limit` cuốn.", "mô tả là phần trước Args:"
    params = f["parameters"]
    assert params["type"] == "object" and params["additionalProperties"] is False
    assert list(params["properties"]) == ["query", "limit", "category", "in_stock", "author"], "đúng thứ tự tham số"
    assert params["required"] == ["query"], "chỉ tham số không có mặc định là required"
    jsonschema.Draft202012Validator.check_schema(params)


def test_tool_spec_properties(t):
    props = t.tool_spec(search_books)["function"]["parameters"]["properties"]
    assert props["query"] == {"type": "string", "description": "một phần tên sách hoặc tên tác giả"}
    assert props["limit"] == {"type": "integer", "description": "số kết quả tối đa, từ 1 tới 20", "default": 5}
    assert props["category"] == {"type": ["string", "null"], "enum": ["văn học", "thiếu nhi", None],
                                 "description": "lọc theo thể loại"}
    assert props["in_stock"] == {"type": "boolean", "default": True}
    assert props["author"] == {"type": ["string", "null"]}, "mặc định None không ghi vào schema"


def test_tool_spec_without_docstring(t):
    def ping(x: float) -> float:
        return x

    f = t.tool_spec(ping)["function"]
    assert f["description"] == ""
    assert f["parameters"]["properties"] == {"x": {"type": "number"}}
    assert f["parameters"]["required"] == ["x"]


def test_tool_spec_rejects_bad_signatures(t):
    def no_hint(x):
        return x

    def var_args(*items: str) -> str:
        return ""

    def var_kwargs(**opts: str) -> str:
        return ""

    for fn in (no_hint, var_args, var_kwargs):
        with pytest.raises(TypeError):
            t.tool_spec(fn)


# ---------- ToolRegistry ----------


def make_registry(t):
    reg = t.ToolRegistry()

    @reg.register
    def get_price(book_id: str, currency: Literal["VND", "USD"] = "VND") -> dict:
        """Giá sách."""
        if book_id == "B404":
            raise KeyError("không có sách B404")
        return {"book_id": book_id, "giá": 110000 if currency == "VND" else 4.33}

    @reg.register
    def greet(name: str) -> str:
        """Chào."""
        return f"Xin chào {name}"

    return reg, get_price


def test_register_and_specs(t):
    reg, fn = make_registry(t)
    assert callable(fn) and fn.__name__ == "get_price", "register trả lại chính hàm (dùng như decorator)"
    assert [s["function"]["name"] for s in reg.specs()] == ["get_price", "greet"]
    assert reg.specs()[0] == t.tool_spec(fn)

    def greet(name: str) -> str:
        return name

    with pytest.raises(ValueError):
        reg.register(greet)


def test_call_success(t):
    reg, _ = make_registry(t)
    obs = reg.call("get_price", {"book_id": "B05"})
    assert obs.ok is True
    assert json.loads(obs.content) == {"book_id": "B05", "giá": 110000}
    assert "giá" in obs.content, "giữ tiếng Việt (ensure_ascii=False)"
    assert reg.call("get_price", '{"book_id": "B05", "currency": "USD"}').content == json.dumps(
        {"book_id": "B05", "giá": 4.33}, ensure_ascii=False)
    assert reg.call("greet", {"name": "Lan"}) == t.Observation(True, "Xin chào Lan"), "chuỗi trả về giữ nguyên"


def test_call_unknown_tool_lists_valid_names(t):
    reg, _ = make_registry(t)
    obs = reg.call("get_prices", {"book_id": "B05"})
    assert obs.ok is False and obs.content.startswith("ERROR: ")
    assert "get_prices" in obs.content and "get_price" in obs.content and "greet" in obs.content


@pytest.mark.parametrize("args", ['{"book_id": "B05"', "B05", '["B05"]', ["B05"], 42, None])
def test_call_arguments_not_object(t, args):
    reg, _ = make_registry(t)
    obs = reg.call("get_price", args)
    assert obs.ok is False and obs.content.startswith("ERROR: ")
    assert "get_price" in obs.content


def test_call_schema_errors_are_explained(t):
    reg, _ = make_registry(t)
    bad_enum = reg.call("get_price", {"book_id": "B05", "currency": "JPY"})
    assert bad_enum.ok is False and "JPY" in bad_enum.content and "currency" in bad_enum.content
    missing = reg.call("get_price", {})
    assert missing.ok is False and "book_id" in missing.content
    extra = reg.call("get_price", {"book_id": "B05", "discount": 10})
    assert extra.ok is False and "discount" in extra.content, "additionalProperties: False chặn tham số lạ"
    wrong_type = reg.call("get_price", {"book_id": 5})
    assert wrong_type.ok is False and "book_id" in wrong_type.content


def test_call_bool_is_not_integer(t):
    reg = t.ToolRegistry()

    @reg.register
    def repeat(times: int) -> int:
        return times

    assert reg.call("repeat", {"times": 3}).ok
    assert reg.call("repeat", {"times": True}).ok is False


def test_call_optional_accepts_null(t):
    reg = t.ToolRegistry()
    reg.register(search_books)
    obs = reg.call("search_books", {"query": "Mắt biếc", "category": None})
    assert obs.ok, obs.content
    assert json.loads(obs.content)[0]["category"] is None


def test_call_exception_becomes_observation(t):
    reg, _ = make_registry(t)
    obs = reg.call("get_price", {"book_id": "B404"})
    assert obs.ok is False and obs.content.startswith("ERROR: ")
    assert "KeyError" in obs.content and "B404" in obs.content
