# Lời giải: JSON từ LLM

## Cách làm

- `extract_json`: duyệt từng vị trí có `{` hoặc `[`, thử `json.JSONDecoder().raw_decode(text, i)`; lần đầu thành công
  thì trả. `raw_decode` tự xử lý ngoặc trong chuỗi và bỏ qua phần chữ sau JSON, nên không cần tự đếm ngoặc.
- `validate`: bảng `TYPES` ánh xạ tên kiểu sang hàm kiểm (`integer` và `number` loại `bool`); kiểm `type` (một hoặc
  nhiều kiểu), sai thì trả ngay một lỗi; rồi `enum`; với object: `required`, đệ quy vào `properties` với đường dẫn
  `path.key`, báo khoá thừa khi `additionalProperties` là `false`; với array: `minItems`, `maxItems`, đệ quy `items` với
  `path[i]`; với chuỗi: độ dài; với số: `minimum`, `maximum`.
- `generate_validated`: vòng `max_retries + 1` lần; mỗi lần gọi với `json_schema=schema`, gom lỗi tách/kiểm vào một
  list; hợp lệ thì trả; sai thì tạo lịch sử **mới** (`history + [...]`) gồm câu trả lời sai và feedback liệt kê lỗi.

## Vì sao các lựa chọn này

- **Kiểm phía client dù server đã ép schema**: `format` của Ollama và `response_format` kiểu `json_schema` ràng buộc
  việc **sinh token** (constrained decoding), nên JSON gần như luôn parse được. Nhưng (mục 5 lý thuyết) câu trả lời bị
  cắt ở `num_predict` vẫn là JSON dở dang, gateway có thể bỏ qua schema mà không báo, một số server chỉ hỗ trợ một
  phần JSON Schema (ví dụ không ép `minimum`, `maxLength`), và model ở chế độ "JSON mode" không có schema thì chỉ bảo
  đảm JSON hợp lệ, không bảo đảm đúng khoá.
- **Đường dẫn trong thông báo lỗi**: model sửa được lỗi khi được chỉ đúng chỗ (`$.sentiment: 'tiêu cực' không thuộc
  enum [...]`); "JSON sai" chung chung thường cho lại đúng câu trả lời cũ ở temperature 0.
- **Đưa câu trả lời sai vào lịch sử** thay vì gửi lại prompt gốc: ở temperature 0, gửi lại y nguyên prompt thì gần như
  chắc chắn nhận lại y nguyên câu trả lời. Mỗi lần gọi lại tốn thêm toàn bộ prompt, nên giữ `max_retries` nhỏ (1 tới 2)
  và đếm số lần gọi lại như một thước đo chất lượng prompt.
- **`ExtractionError` mang mọi lần thử**: khi xử lý lô hàng nghìn câu, ghi lại lỗi để phân tích sau quan trọng hơn
  việc dừng ở câu đầu tiên hỏng.

## Bẫy thường gặp

- Cắt chuỗi từ `{` đầu tiên tới `}` cuối cùng: hỏng khi có hai object, hoặc khi đoạn giả JSON đứng trước.
- `isinstance(True, int)` là `True` trong Python: `"severity": true` lọt qua kiểm integer.
- Báo lỗi thiếu khoá ở `$.topic` (khoá không tồn tại) thay vì ở object chứa nó; mỗi thư viện có quy ước riêng, quan
  trọng là nhất quán và model hiểu được.
- Sửa thẳng `messages` của người gọi bằng `append` trong vòng gọi lại.
- Dùng `pydantic` hay `jsonschema` ở production là đúng; bài này viết tay để bạn biết chúng kiểm gì.
