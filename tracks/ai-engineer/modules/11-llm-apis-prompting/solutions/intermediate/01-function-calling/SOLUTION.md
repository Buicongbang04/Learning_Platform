# Lời giải: function calling viết tay

## Cách làm

- `make_registry(df)`: một hàm phụ `select(topic, sentiment)` lọc `DataFrame` (tham số `None` thì không lọc, chuyển tên
  sang mã bằng `TOPICS.index`, `SENTIMENTS.index`); ba tool là closure dùng chung nó. `count` ép `int(...)` vì
  `numpy.int64` không `json.dumps` được.
- `execute_tool_call`: tra spec theo tên; parse `arguments` (dict giữ nguyên, chuỗi thì `json.loads`, kết quả phải là
  dict); `jsonschema.Draft202012Validator(parameters).iter_errors(args)` gom mọi lỗi; gọi hàm trong `try/except
  Exception`. Mỗi nhánh lỗi trả `"ERROR: ..."` có thông tin để sửa (danh sách tool hợp lệ, `e.message` của jsonschema
  như `'phòng học' is not one of [...]`, tên exception).
- `run_tool_loop`: sao chép `messages`; vòng tối đa `max_steps` lần gọi `chat`; không có tool call thì trả lời; có thì
  gán id thiếu `call_<bước>_<i>`, thêm message assistant, thực thi tuần tự, thêm message `tool`, ghi `(tên, arguments,
  kết quả)` và đếm lỗi. Hết vòng thì `stopped="max_steps"`.
- `prompted_chat(llm)`: trả closure `chat(messages, tools)`: system giao thức (mỗi tool một dòng với
  `json.dumps(parameters)`, hai dạng JSON trả lời, "không bịa số"), đổi assistant có tool call thành chuỗi JSON và
  message `tool` thành message user "Kết quả tool ...", gọi `llm.chat(history, json_schema=PROMPTED_SCHEMA)`, parse.

## Vì sao các lựa chọn này

- **Lỗi là kết quả, không phải exception**: model đọc được "ERROR: ... 'phòng học' is not one of ['lecturer', ...]" và
  sửa ở lượt sau (thí nghiệm cuối notebook). Exception thì giết cả hội thoại vì một tham số sai.
- **Validate bằng schema của chính tool**: một nguồn sự thật cho cả model (đọc schema để sinh tham số) và code (kiểm
  tham số). `additionalProperties: false` bắt model bịa tham số (`year`).
- **`max_steps`**: model nhỏ đôi khi gọi lại đúng tool đó mãi; không có giới hạn là một vòng lặp tốn tiền vô hạn.
- **Id do code đặt khi thiếu**: Ollama không trả id cho tool call; không có id thì không ghép được kết quả với lời gọi
  khi có nhiều call song song.
- **Prompted chỉ dùng chuỗi**: chạy được với bất kỳ LLM nào sau `llmkit.chat`, kể cả model không được fine-tune cho tool
  call. Cái giá: phải tự mô tả giao thức, tự đổi lịch sử, và model có thể vừa gọi tool vừa trả lời (ưu tiên tool call).

## Kết quả tham chiếu

§§M4REF§§

## Bẫy thường gặp

- Để `json.dumps` gặp `numpy.int64` từ `len(df[...])` hay `df.sum()`: lỗi ở lớp tool làm mọi câu đếm thành `ERROR`.
- Bắt `json.JSONDecodeError` nhưng quên trường hợp JSON hợp lệ mà không phải object (`'["facility"]'`).
- Thêm message `tool` trước message assistant chứa tool call, hoặc quên `tool_call_id`: API thật trả 400, model local thì
  hiểu sai.
- Đếm `steps` theo số tool call thay vì số lần gọi model; `max_steps` khi đó cắt sai chỗ.
- Tin model tự tính phần trăm: model nhỏ làm tròn sai hoặc chia ngược. Tool `percentage` tồn tại để số học nằm trong code.
