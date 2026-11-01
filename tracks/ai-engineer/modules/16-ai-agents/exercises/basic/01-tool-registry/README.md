---
title: Tool registry - JSON Schema sinh từ chữ ký hàm, lỗi thành Observation
level: basic
services: []
files:
  - path: starter/tools.py
    note: schema_for, tool_spec, ToolRegistry (3 phương thức) TODO
  - path: tests/test_tools.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/16-ai-agents/exercises/basic/01-tool-registry -q
---

## Mục tiêu

Viết lớp đầu tiên của một agent không framework: biến hàm Python bình thường thành tool mà LLM đọc được (spec JSON
Schema sinh từ type hint và docstring, như `@tool` của các framework và `@server.tool()` của SDK MCP), và gọi tool
theo tên với tham số do model sinh ra mà **không bao giờ** làm sập vòng lặp. Module 11 bài Intermediate 01 đã viết
`execute_tool_call` với spec viết tay; bài này tự động hoá phần spec và đóng gói thành registry dùng lại cho cả module.

## Đề bài

**Phần cứng:** CPU · ~50 phút

Trong `starter/tools.py` (`parse_docstring` đã có):

1. `schema_for(annotation, where="") -> dict`: JSON Schema của một type hint: `int`, `float`, `str`, `bool`,
   `list[T]`, `Literal[...]` (toàn chuỗi hoặc toàn số nguyên), `T | None` (cho phép `null`, có enum thì thêm `None`
   vào enum). Kiểu khác thì `TypeError` có nêu `where` (ví dụ `"search_books.limit"`).
2. `tool_spec(fn) -> dict`: spec dạng OpenAI `{"type": "function", "function": {"name", "description",
   "parameters"}}`. `parameters` là object có `properties` theo đúng thứ tự tham số, `required` là các tham số không
   có giá trị mặc định, `additionalProperties: false`; mô tả hàm và mô tả từng tham số lấy từ docstring kiểu Google
   (`Args:`); mặc định khác `None` ghi vào `default`. Thiếu type hint, `*args`, `**kwargs` thì `TypeError`.
3. `ToolRegistry`: `register(fn)` (dùng được như decorator, trùng tên thì `ValueError`), `specs()` theo thứ tự đăng
   ký, `call(name, arguments) -> Observation(ok, content)`. `arguments` là dict hoặc chuỗi JSON. Thành công: chuỗi
   giữ nguyên, kiểu khác thì `json.dumps(..., ensure_ascii=False)`. Mọi lỗi (tool không có, tham số không phải JSON
   object, sai schema theo `jsonschema`, hàm ném exception) thành `Observation(False, "ERROR: ...")` có đủ thông tin
   để model tự sửa ở lượt sau: tên các tool hợp lệ, tên tham số và giá trị sai, tên lớp exception.

Docstring của từng hàm trong starter nêu đúng quy ước. Đọc mục 2 lý thuyết (tool registry, lỗi là observation).

## Tiêu chí đạt

- `schema_for`: đúng 4 kiểu nguyên thuỷ (`bool` không thành `integer`), `list` lồng nhau, enum chuỗi và enum số nguyên,
  `T | None` và `Optional[T]` cho `["<type>", "null"]`; `dict`, `tuple`, `int | str`, `Literal` lẫn kiểu, `set` đều
  `TypeError`.
- `tool_spec` trên một hàm 5 tham số có docstring nhiều dòng: mô tả hàm không lẫn phần `Args`/`Returns`, mô tả tham
  số viết trên hai dòng được nối lại, chỉ `query` là required, `limit` có `default: 5`, tham số mặc định `None` không
  có `default`; `parameters` qua được `Draft202012Validator.check_schema`.
- `ToolRegistry.call`: tiếng Việt không bị escape; tham số sai enum nêu giá trị sai và tên tham số; thiếu tham số bắt
  buộc, tham số lạ, sai kiểu, `true` cho tham số `integer` đều bị chặn; `null` cho tham số `T | None` được nhận;
  exception của hàm thành `ERROR:` có tên lớp exception.

## Gợi ý

### Gợi ý 1

`typing.get_origin` và `typing.get_args` tách `list[str]` thành `(list, (str,))`, `Literal["a", "b"]` thành
`(Literal, ("a", "b"))`. `int | None` (cú pháp mới) và `Optional[int]` có origin khác nhau (`types.UnionType` và
`typing.Union`): kiểm cả hai. Dùng `typing.get_type_hints(fn)` thay cho `fn.__annotations__` để hint dạng chuỗi
cũng được giải.

### Gợi ý 2

`inspect.signature(fn).parameters` giữ đúng thứ tự tham số; `param.default is inspect.Parameter.empty` nghĩa là
không có mặc định. Với `jsonschema`, `Draft202012Validator(schema).iter_errors(args)` trả mọi lỗi một lần (không dừng
ở lỗi đầu), mỗi lỗi có `.message` và `.path`; ghép chúng thành một thông báo. Bọc lời gọi hàm trong
`try/except Exception`: tool lỗi là chuyện thường, agent phải thấy lỗi và tự sửa.
