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

Chạy cell `explore` của lời giải ngày 2026-11-01 trên PC của track (`qwen2.5:3b` qua Ollama 0.13.5, `temperature` 0,
`seed` 0, RTX 3060 **dùng chung** với một job train khác, nên số giây chỉ để so tương đối):

| Cách | Đúng / 12 | Bước trung bình | Tool call | Lỗi tool | Giây trung bình |
| --- | --- | --- | --- | --- | --- |
| native | 7 | 1.92 | 13 | 1 | 1.38 |
| prompted | 6 | 1.92 | 11 | 1 | 3.86 |

Đáp án tính từ dữ liệu: 3 166 phản hồi; 138 tiêu cực về cơ sở vật chất trên 145; 1 590 tích cực; 572 về chương trình
đào tạo; 44 trung tính thuộc `others`; giảng viên 1 425 tích cực, 791 tiêu cực; phần trăm 95.2, 5.3, 72.7, 89.6.

- Cả hai cách đúng mọi câu **một lần đếm** (trừ câu tổng), câu `list_examples` và câu ngoài phạm vi.
- Cả hai sai **cả bốn** câu phần trăm, mỗi câu một kiểu:

  | Câu | Native | Prompted |
  | --- | --- | --- |
  | tiêu cực / cơ sở vật chất | đếm đúng 138, rồi `percentage(10, 50)` với số bịa, trả 20% | đếm 138, tự viết 27.6% |
  | trung tính / toàn tập | không đếm, `percentage(1234, 56789)`, trả 2.2% | không đếm, `percentage(1234567890, 1500000000)`, trả 82.3% |
  | tiêu cực / chương trình đào tạo | đếm 416, không gọi `percentage`, hỏi lại người dùng tổng số | đếm 416, tự viết 41.6% |
  | giảng viên / tích cực | không đếm, `percentage(234, 1000)`, trả 23.4% | đếm 1 425, tự viết 53.8% |

  Prompted còn sai câu hai số đếm (chỉ đếm lớp tích cực).
- Câu "tổng bao nhiêu phản hồi": cả hai gửi `topic: null`, `sentiment: null`; schema chỉ cho chuỗi nên tool trả lỗi
  (lỗi tool duy nhất của mỗi cách). Native hỏi lại người dùng, prompted bịa "123456789".
- Câu ngoài phạm vi: prompted trả `answer` rỗng (schema không bắt buộc `answer`), vẫn tính đúng theo tiêu chí "không
  gọi tool".
- Thí nghiệm tự sửa (`topic: "phòng học"`, một lần thử mỗi cách): prompted gọi lại với `facility` và trả lời đúng 138;
  native không gọi lại.

Đọc: chênh 7 và 6 trên 12 câu là nhiễu. Bài học nằm ở **thiết kế tool**: model 3B không tự lập kế hoạch "đếm, đếm,
chia"; một tool trả thẳng phần trăm theo bộ lọc, và schema cho phép `null` ở tham số lọc, sẽ sửa phần lớn lỗi mà không
đổi model. Chạy lại trên máy khác (nhất là chỉ CPU) có thể lệch một hai câu.

## Bẫy thường gặp

- Để `json.dumps` gặp `numpy.int64` từ `len(df[...])` hay `df.sum()`: lỗi ở lớp tool làm mọi câu đếm thành `ERROR`.
- Bắt `json.JSONDecodeError` nhưng quên trường hợp JSON hợp lệ mà không phải object (`'["facility"]'`).
- Thêm message `tool` trước message assistant chứa tool call, hoặc quên `tool_call_id`: API thật trả 400, model local thì
  hiểu sai.
- Đếm `steps` theo số tool call thay vì số lần gọi model; `max_steps` khi đó cắt sai chỗ.
- Tin model tự tính phần trăm: model nhỏ làm tròn sai hoặc chia ngược. Tool `percentage` tồn tại để số học nằm trong code.
