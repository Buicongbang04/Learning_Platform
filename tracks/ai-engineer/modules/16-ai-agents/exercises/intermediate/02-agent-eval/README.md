---
title: Đánh giá agent trên bộ task ghim - ReAct, native, JSON, khoảng tin cậy và phân loại lỗi
level: intermediate
services: []
files:
  - path: starter/agent_eval.ipynb
    note: dán bài Basic 01-02, 5 hàm TODO
  - path: starter/bookstore.py
    note: Môi trường hiệu sách, 5 tool, 24 task (không sửa)
  - path: tests/test_agent_eval.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/16-ai-agents/exercises/intermediate/02-agent-eval/starter/agent_eval.ipynb
  - uv run pytest tracks/ai-engineer/modules/16-ai-agents/exercises/intermediate/02-agent-eval -q
---

## Mục tiêu

Đo agent như đo một model: bộ task ghim có đáp án tính từ dữ liệu, chấm tự động câu trả lời tự do tiếng Việt, khoảng
tin cậy cho tỉ lệ thành công, so theo cặp, và phân loại lỗi tự động từ trace. Rồi dùng chính bộ đo đó so ba cách gọi
tool trên `qwen2.5:3b`: vòng ReAct văn bản của bạn, native tool calling của Ollama, và ReAct ép JSON schema.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Thời gian trên là thời gian làm bài. Các cell `explore` gọi model khoảng 250 lượt: chạy khoảng 10 tới 15 phút trên PC
của track (`qwen2.5:3b` trên GPU dùng chung); laptop GPU 4GB chậm hơn, CPU thuần chậm hơn nhiều.

`starter/bookstore.py` là một hiệu sách tự tạo: 24 cuốn sách, 4 đơn hàng, tỷ giá ghim, 5 tool (`search_books`,
`get_book`, `get_order`, `calculator`, `exchange_rate`), và 24 task có đáp án tính từ dữ liệu (tra một lần, tính toán,
đơn hàng nhiều bước, ngoại tệ, so sánh, câu không cần tool).

Trong `starter/agent_eval.ipynb`:

1. Dán lời giải bài Basic 01 và Basic 02 vào cell đầu (notebook tự chứa).
2. `numbers_in(text)`: mọi con số trong câu trả lời tiếng Việt theo quy ước ghi trong notebook (phân cách hàng nghìn,
   dấu thập phân, "triệu", "nghìn").
3. `check_answer(answer, expected)`: mọi chuỗi phải có, mọi số phải khớp với sai lệch không quá 0.01.
4. `wilson_interval(k, n, z=1.96)`, `discordant(a, b)` (các task chỉ một bên đúng), `classify_failure(row)` (6 nhãn
   theo thứ tự ưu tiên ghi trong notebook: `ok`, `no_answer`, `no_tool`, `hallucinated_number`, `tool_error`,
   `wrong_other`).

Rồi chạy các cell `explore`: ba cách trên 24 task, bảng có khoảng tin cậy và số cặp lệch nhau, bảng theo nhóm task,
phân loại lỗi kèm trace của từng task sai, và một cell mở rộng (không chấm) thêm 20 tool gây nhiễu. Sau đó làm phần
trắc nghiệm của bài trong app. Câu trả lời của model có thể lệch giữa các máy và phiên bản Ollama; các câu trắc nghiệm
số liệu lấy từ lần chạy của lời giải mẫu và hỏi theo khoảng hoặc theo thứ tự.

## Tiêu chí đạt

- `numbers_in` đúng trên 10 chuỗi mẫu (hàng nghìn bằng `.`, `,`, dấu cách; thập phân; "triệu", "nghìn", "ngàn"; số dính
  chữ); `check_answer` đúng cả với đáp án làm tròn 2 chữ số và đáp án nhiều phần; mọi task trong `bookstore.TASKS` có
  một câu trả lời mẫu được chấm đúng.
- `wilson_interval(17, 24)` khoảng `[0.508, 0.851]`; trường hợp `k = 0`, `k = n`, `n = 0` đúng.
- `discordant` đúng hai chiều, báo lỗi khi hai bên khác bộ task.
- `classify_failure` đúng thứ tự ưu tiên, so số trong câu trả lời với số của **mọi** observation và câu hỏi.
- Các cell `explore` chạy hết với `qwen2.5:3b`.

## Gợi ý

### Gợi ý 1

Viết một regex có hai nhánh: nhánh "nhóm 3 chữ số" (`\d{1,3}(?:[., ]\d{3})+`) thử trước, nhánh "số thường có tối đa
một dấu thập phân" sau. Cẩn thận với `5.3150`: không phải nhóm 3 chữ số, nên là thập phân. Thử hàm trên mọi chuỗi
mẫu trong test trước khi chạy cả bộ.

### Gợi ý 2

Công thức Wilson nằm trong notebook; kẹp kết quả vào `[0, 1]` (sai số làm tròn có thể cho `-1e-17`). Với
`classify_failure`, gom mọi số trong câu hỏi và mọi observation vào một danh sách rồi kiểm từng số của câu trả lời;
nhớ áp quy ước của `numbers_in` cho cả observation.
