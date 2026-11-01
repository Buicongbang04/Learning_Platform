# Lời giải: vòng ReAct

## Parser

`clean_reply` cắt ở dòng `Observation:` đầu tiên **trước** mọi việc khác. Model nhỏ hay viết tiếp cả observation tưởng
tượng lẫn câu trả lời cuối trong cùng một lượt ("Action: search_books ... Observation: giá 99.000 ... Final Answer:
99.000 đồng"); nếu không cắt, parser thấy `Final Answer` và agent trả lời bằng số bịa mà không gọi tool. Với API cho
phép, đặt `stop=["Observation:"]` để server cắt luôn (Ollama: `options.stop`), nhưng parser vẫn phải tự cắt vì không
phải server nào cũng có.

Thứ tự quyết định: `Action` đứng trước `Final Answer` thì là action (model muốn hành động rồi tự bịa phần sau);
ngược lại là câu trả lời. Tham số đọc bằng `json.JSONDecoder().raw_decode` sau khi bỏ hàng rào ```` ``` ````: nó đọc
đúng một giá trị JSON và bỏ qua chữ thừa phía sau, thứ `json.loads` không làm được. Regex `^\s*Action\s*:` với
`re.M` không khớp `Action Input:` (sau `Action` là khoảng trắng rồi `Input`, không phải dấu hai chấm).

Mỗi `ReActParseError` nói **thiếu gì**: "Thiếu dòng `Action Input:` (JSON object) cho tool run_tests" giúp model sửa
đúng chỗ ở lượt sau; "parse error" thì không.

## Vòng lặp

Mỗi bước là một nhánh của máy trạng thái (sơ đồ ở mục 2 lý thuyết):

| Nhánh | messages thêm | Step | Dừng? |
| --- | --- | --- | --- |
| `LLMError` | không | không | có, `llm_error` |
| lỗi định dạng | assistant nguyên văn + user "Lỗi định dạng: ..." | `format_error` | khi lỗi liên tiếp > `max_format_retries` |
| `Final` | assistant đã cắt | `final` | có, `answer` |
| action lặp | không | `repeat` | có, `repeated_action` |
| action | assistant đã cắt + user "Observation: ..." | `action` | không |

Ba quyết định đáng nói:

- **Đếm lỗi định dạng liên tiếp**, không đếm tổng: một lỗi giữa chừng rồi sửa được là bình thường; ba lỗi liền nhau
  nghĩa là model không hiểu giao thức, gọi tiếp chỉ tốn tiền.
- **Phát hiện lặp theo tham số đã parse** (`json.dumps(args, sort_keys=True)`), không theo chữ: model đổi câu
  Thought nhưng gọi đúng tool cũ với đúng tham số cũ vẫn là lặp. Bản tham chiếu dừng hẳn; bài Advanced 01 cho thấy một
  lựa chọn khác (trả observation nhắc model làm bước khác) đôi khi cứu được lượt chạy.
- **Lưu reply đã cắt vào lịch sử**: lượt sau model không thấy observation bịa của chính nó.

`max_steps` đếm **mọi** lần gọi LLM (kể cả lượt lỗi định dạng), vì đó là thứ tốn tiền và thời gian thật.

## Bẫy thường gặp

- Tìm `"Final Answer"` trước `"Action"`: agent trả lời bằng số bịa sau observation tưởng tượng.
- `json.loads` cả phần sau `Action Input:`: hỏng khi model viết thêm một câu sau JSON.
- Sửa list `history` của người gọi (append vào chính nó): lần chạy sau thấy cả lịch sử của lần trước.
- `FakeLLM.calls` giữ **tham chiếu** tới `messages`; test của bài dùng bản sao. Khi tự viết test cho vòng lặp, nhớ chép
  `messages` lúc gọi, nếu không mọi phần tử của `calls` trông giống hệt nhau.
- Bắt mọi `Exception` quanh `llm.chat`: che mất lỗi lập trình trong chính vòng lặp. Chỉ bắt `llmkit.LLMError`.
