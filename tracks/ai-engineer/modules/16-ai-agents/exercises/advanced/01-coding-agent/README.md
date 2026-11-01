---
title: Coding agent trong sandbox, chấm bằng test ẩn, pass@1 và phân tích lỗi (portfolio)
level: advanced
services: []
files:
  - path: starter/sandbox.py
    note: safe_path, run_pytest, grade TODO
  - path: starter/agent.ipynb
    note: Môi trường agent, vòng lặp, chạy bộ task
  - path: starter/tasks
    note: 12 task (TASK.md, repo/, hidden/test_hidden.py), không sửa
  - path: starter/REPORT.md
    note: Báo cáo pass@1 và phân tích lỗi
  - path: tests/test_sandbox.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - uv run pytest tracks/ai-engineer/modules/16-ai-agents/exercises/advanced/01-coding-agent -q
  - uv run jupyter lab tracks/ai-engineer/modules/16-ai-agents/exercises/advanced/01-coding-agent/starter/agent.ipynb
---

## Mục tiêu

Dựng một coding agent hoàn chỉnh chạy local và đo nó như người ta đo SWE-bench: bộ task ghim, mã của agent chạy trong
sandbox (thư mục tạm, tiến trình con có timeout, không mạng, môi trường tối thiểu), kết quả chấm bằng **test ẩn** mà
agent không thấy và không sửa được. Báo pass@1 của `qwen2.5:3b` với seed và `temperature` cố định, so ít nhất hai thiết
kế agent, và phân loại lỗi trung thực. Đây là bài portfolio: một con số thấp được đo đúng và giải thích được.

## Đề bài

**Phần cứng:** CPU · ~360 phút

Thời gian trên là thời gian làm bài (sandbox, agent, chạy, đọc trace, viết báo cáo). Một lượt cả bộ 12 task với
`qwen2.5:3b` chạy khoảng 5 tới 8 phút trên PC của track (GPU dùng chung), lâu hơn trên laptop; bài cần vài lượt.
`qwen2.5:7b` (tuỳ chọn, PC 12GB) mỗi bước chậm hơn nhưng cần ít bước hơn, một lượt cũng cỡ 4 tới 8 phút trên PC; trên
laptop 4GB nó chạy được nhưng chậm (model không vừa hết VRAM), bỏ qua cũng được.

`starter/tasks/` có 12 task tự tạo, gồm task viết hàm theo mô tả (định dạng tiền đồng, slug tiếng Việt, số La Mã,
run-length encoding, số căn cước, số điện thoại...) và task sửa bug trong mã có sẵn. Mỗi task có `TASK.md`, `repo/` (mã khởi đầu và
`tests/test_visible.py` với 1 test) và `hidden/test_hidden.py` (3 tới 10 test, gồm cả trường hợp biên). Agent chỉ thấy
`repo/`.

1. `starter/sandbox.py` (có test): `safe_path`, `run_pytest` (tiến trình con, môi trường tối thiểu, `unshare -rn` nếu có,
   timeout giết cả nhóm tiến trình, đọc số pass/fail/error), `grade` (chép mã nguồn của agent, **không** chép test của
   agent, sang thư mục sạch cùng test ẩn).
2. `starter/agent.ipynb`: môi trường của agent (tool đọc, ghi, liệt kê tệp, chạy test thấy được) và vòng lặp. Dùng lại
   `parse_react`/`run_react` của bài Basic 02 hoặc tự viết. Mỗi lượt chạy ghi: task, pass/fail theo test ẩn và test thấy
   được, lý do dừng, số bước, số lần ghi tệp, số lần chạy test, số lỗi định dạng, có sửa `tests/` không, thời gian, trace.
3. Đo:
   - pass@1 của `qwen2.5:3b`, `temperature` 0, `seed` 0, trên cả 12 task;
   - ít nhất **hai thiết kế agent** khác nhau trên cùng bộ (ví dụ: agent tự đọc tệp và ghi bằng JSON, so với agent được
     đưa sẵn nội dung tệp và ghi bằng khối code);
   - ít nhất 3 seed với `temperature` 0.7 cho thiết kế tốt nhất, báo khoảng dao động;
   - taxonomy lỗi có đếm.
4. Viết `starter/REPORT.md` theo khung, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt**:

- Mở bằng con số và kết luận ("pass@1 X/12 ở `temperature` 0, Y tới Z/12 qua 3 seed; thay đổi giúp nhiều nhất là ...").
- Bảng theo task và theo cấu hình, có cột "test thấy được pass" cạnh "test ẩn pass": chênh lệch giữa hai cột là phát
  hiện quan trọng nhất của một coding agent.
- Phân tích lỗi bằng trace thật: không bao giờ ghi tệp, lỗi định dạng, lặp, hết bước, test thấy được pass mà test ẩn
  fail, sửa test thay vì sửa mã. Mỗi loại bao nhiêu task.
- Sandbox: những gì nó chặn được và không chặn được (giới hạn bộ nhớ? tiến trình nền? đọc tệp ngoài thư mục bằng mã
  Python chứ không qua tool?).
- Giới hạn: 12 task, task tự tạo và nhỏ hơn nhiều so với issue thật, một model.

## Tiêu chí đạt

- Test của `sandbox.py` pass: đường dẫn ra ngoài (kể cả qua symlink) bị chặn; đếm đúng pass/fail/error (kể cả lỗi
  import khi thu thập test); timeout giết cả tiến trình cháu; biến môi trường của bạn không lọt vào sandbox; mạng bị
  chặn khi máy có `unshare`; `grade` dùng test ẩn, bỏ qua test agent đã sửa và các tệp `conftest.py`/`sitecustomize.py` agent tự ghi, không
  sửa thư mục của agent.
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`subprocess.Popen(..., start_new_session=True)` đặt tiến trình con vào một nhóm tiến trình mới; khi quá giờ,
`os.killpg(proc.pid, signal.SIGKILL)` giết cả nhóm (một test có thể tự sinh tiến trình con, `proc.kill()` chỉ giết
tiến trình đầu). Dòng cuối của `pytest -q` có dạng `2 passed, 1 failed in 0.05s` hoặc `1 error in 0.09s`: đọc bằng regex
`(\d+) (passed|failed|errors?)`. Với `safe_path`, so đường dẫn **sau** `resolve()` (resolve đi theo symlink).

### Gợi ý 2

Model 3B gặp khó nhất ở **giao diện**, không phải ở thuật toán: viết cả tệp mã trong một chuỗi JSON phải escape mọi
xuống dòng và dấu nháy, và model hay dùng `'''` của Python thay cho chuỗi JSON. Thử cho phép nội dung tệp nằm trong một
khối ```` ```python ```` ngay sau `Action Input`, đưa sẵn nội dung các tệp vào lượt đầu, và chạy `pytest --tb=short` để
output lỗi ngắn mà vẫn có dòng assert. Đọc trace của từng task trước khi đổi thêm thứ gì: mỗi thay đổi thiết kế nên
nhắm một loại lỗi bạn đã đếm được.
