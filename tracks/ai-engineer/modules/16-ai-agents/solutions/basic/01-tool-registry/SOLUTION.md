# Lời giải: tool registry

## Cách làm

**`schema_for`** xử lý theo thứ tự: kiểu nguyên thuỷ tra bảng (`bool` là lớp con của `int` trong Python, nhưng tra
bằng `annotation in _PRIMITIVES` so **đúng kiểu** nên `bool` không lẫn thành `integer`); rồi `typing.get_origin`:
`Literal` (kiểm mọi giá trị cùng kiểu), `list` (gọi đệ quy cho kiểu phần tử), `Union` của đúng hai nhánh trong đó một
nhánh là `NoneType`. `T | None` và `Optional[T]` cho origin khác nhau (`types.UnionType` và `typing.Union`), phải kiểm
cả hai. Mọi kiểu còn lại ném `TypeError` có tên hàm và tên tham số: lỗi spec phải lộ ra lúc **đăng ký** tool, không phải
lúc model gọi nó giữa một hội thoại.

**`tool_spec`** duyệt `inspect.signature(fn).parameters` (giữ thứ tự khai báo), lấy hint qua `typing.get_type_hints`
(giải được hint dạng chuỗi khi có `from __future__ import annotations`). Tham số không có mặc định vào `required`.
Mặc định `None` không ghi `default` vì nó đã được diễn đạt bằng `"null"` trong `type`, và ghi `"default": null` làm
nhiều model tưởng phải truyền `null`.

**`ToolRegistry.call`** đi qua bốn cửa, mỗi cửa có thông điệp riêng:

| Cửa | Lỗi | Thông điệp cho model |
| --- | --- | --- |
| Tên tool | model bịa tên (`get_prices`) | tên sai + danh sách tool hợp lệ |
| Kiểu tham số | chuỗi không phải JSON, JSON không phải object | tên tool + nguyên văn nhận được |
| Schema | sai enum, thiếu tham số, tham số lạ, sai kiểu | đường dẫn tham số + thông điệp `jsonschema` (nêu giá trị sai) |
| Thực thi | hàm ném exception | tên lớp exception + thông điệp |

`additionalProperties: false` chặn tham số model tự bịa (`discount`), thay vì để Python ném `TypeError: unexpected
keyword argument` khó hiểu. `jsonschema` coi `true` không phải `integer` (khác Python), đúng ý: model viết
`"times": true` là sai.

## Vì sao lỗi là Observation, không phải exception

Trong một agent, lỗi tool là **thông tin** cho model, không phải sự cố của chương trình. Mục 2 lý thuyết đo được
`qwen2.5:3b` đoán mã sách (`get_book("DTNT")`), đọc lỗi "dùng search_books để tìm mã" rồi tự sửa ở lượt sau. Ném
exception thì cả lượt chạy chết vì một tham số sai.

## Bẫy thường gặp

- Kiểm `isinstance(x, int)` cho kiểu `bool`: sai vì `bool` là `int`; so đúng kiểu hoặc tra bảng.
- Dùng `fn.__annotations__`: không giải hint dạng chuỗi, và chứa cả `return`.
- Chỉ báo lỗi đầu tiên của `jsonschema` (`validate` ném ở lỗi đầu): model sửa một lỗi, gặp lỗi tiếp, tốn thêm bước.
- `json.dumps` mặc định `ensure_ascii=True`: "giá" thành `giá`, tốn gấp mấy lần token và model nhỏ đọc kém.
- Bắt `BaseException`: nuốt cả `KeyboardInterrupt`. `Exception` là đủ.
