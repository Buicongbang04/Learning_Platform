---
title: JSON từ LLM - tách, kiểm theo schema, gọi lại khi sai
level: basic
services: []
files:
  - path: starter/structured.py
    note: 3 hàm TODO
  - path: tests/test_structured.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/basic/03-json-output -q
---

## Mục tiêu

Viết lớp phòng thủ mà mọi ứng dụng nhận JSON từ LLM cần, kể cả khi server đã ép schema: tách JSON khỏi câu trả lời
lẫn văn xuôi, kiểm nó theo JSON Schema với thông báo lỗi chỉ đúng chỗ, và vòng gọi lại có phản hồi lỗi cho model.
Sau bài này bạn hiểu `json_schema` của server bảo đảm gì và không bảo đảm gì (mục 5 lý thuyết).

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/structured.py`, chỉ dùng thư viện chuẩn:

1. `extract_json(text)`: giá trị JSON (object hoặc array) **đầu tiên parse được** trong `text`. Model hay bọc JSON
   trong ```` ```json ... ``` ````, thêm câu dẫn, hoặc viết một đoạn trông như JSON mà không phải
   (`{label: positive}`) trước đoạn đúng. Chuỗi trong JSON có thể chứa ngoặc nhọn. Không có thì `ValueError`.
2. `validate(instance, schema, path="$")`: danh sách lỗi theo tập con JSON Schema ghi ở đầu tệp, mỗi lỗi bắt đầu
   bằng **đường dẫn** kiểu JSONPath rồi dấu hai chấm: `$`, `$.topic`, `$.aspects[1]`. Thiếu khoá bắt buộc hoặc thừa
   khoá (khi `additionalProperties` là `false`) báo ở đường dẫn của object. `type` có thể là một chuỗi hoặc danh sách
   (`["string", "null"]`). Hai quy ước của Python cần xử lý tay: `True` **không** phải `integer` hay `number`, và
   trong bài này `1.0` không phải `integer` (thư viện `jsonschema` thì coi là có; test bỏ qua đúng trường hợp đó).
   Sai kiểu thì báo một lỗi và không kiểm tiếp bên trong.
3. `generate_validated(llm, messages, schema, *, max_retries=2)`: gọi `llm.chat(history, json_schema=schema)`, tách và
   kiểm; sai thì thêm vào lịch sử câu trả lời sai (vai `assistant`) và một message `user` liệt kê từng lỗi (có đường
   dẫn), rồi gọi lại. Tối đa `max_retries + 1` lần gọi; hết lượt thì ném `ExtractionError` có `attempts`.

`llm` là bất kỳ thứ gì có `chat(messages, json_schema=...)`: `llmkit.get_client()` khi chạy thật, `FakeLLM` trong
test. Muốn thử thật: dùng schema `SCHEMA` trong test và vài phản hồi UIT-VSFC với `qwen2.5:3b`, đếm bao nhiêu lần
cần gọi lại khi có và không có `json_schema` (mục 5 lý thuyết có số đo).

## Tiêu chí đạt

- `extract_json` đúng 6 ca của test (khối code, văn xuôi bao quanh, ngoặc trong chuỗi, đoạn giả JSON đứng trước,
  array, lồng sâu) và ném `ValueError` với 4 ca không có JSON.
- `validate` bắt 13 lỗi khác nhau đúng đường dẫn, báo đủ hai khoá thiếu, và cho cùng kết luận hợp lệ/không hợp lệ
  với thư viện `jsonschema` trên hơn 50 biến thể.
- `generate_validated`: trả ngay khi lần đầu đúng; lần hai có câu trả lời sai và feedback nêu `$.sentiment`; hết lượt
  thì `ExtractionError` có đủ 3 lần thử; `max_retries=0` chỉ gọi một lần; không sửa `messages` đầu vào.

## Gợi ý

### Gợi ý 1

`json.JSONDecoder().raw_decode(text, i)` parse một giá trị JSON bắt đầu ở vị trí `i` và bỏ qua phần sau nó.

### Gợi ý 2

Viết `validate` đệ quy: kiểm `type` trước (sai thì trả luôn), rồi các ràng buộc theo loại giá trị, và gọi lại chính
nó cho từng thuộc tính và từng phần tử với đường dẫn dài thêm. Một bảng `tên kiểu -> hàm kiểm` giúp gom chỗ xử lý
`bool`.
