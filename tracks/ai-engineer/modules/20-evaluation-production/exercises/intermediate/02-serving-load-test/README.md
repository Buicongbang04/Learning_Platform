---
title: Load test llama.cpp server và Ollama - thông lượng, TTFT, hàng đợi, prefix cache
level: intermediate
services: []
files:
  - path: starter/loadtest.ipynb
    note: 6 hàm TODO
  - path: tests/test_loadtest.py
    note: Không sửa
run:
  - uv sync --group llama
  - uv run --with "starlette-context==0.5.1" python -m llama_cpp.server --help
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull qwen2.5:0.5b-instruct-q4_K_M
  - uv run jupyter lab tracks/ai-engineer/modules/20-evaluation-production/exercises/intermediate/02-serving-load-test/starter/loadtest.ipynb
  - uv run pytest tracks/ai-engineer/modules/20-evaluation-production/exercises/intermediate/02-serving-load-test -q
---

## Mục tiêu

Viết một load generator bất đồng bộ nhỏ (đọc stream SSE, lịch đến Poisson, closed loop và open loop, tóm tắt theo phân vị)
rồi dùng nó trả lời bằng số những câu mà mọi đội tự host model phải trả lời: server chịu bao nhiêu request đồng thời,
TTFT tăng vì đâu, hàng đợi phình thế nào khi tải gần công suất, và prefix cache đáng giá bao nhiêu.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Phần chạy khoảng 10 phút trên PC của track: llama.cpp server chạy CPU 4 luồng. Phần
Ollama giả định Ollama chạy model trên **GPU** (GPU 4GB là đủ cho model 0.5B); số liệu và các câu trắc nghiệm về Ollama đo
trên GPU, chỉ CPU thì số khác hẳn (chưa đo). Cần `uv sync --group llama` (build `llama-cpp-python` từ
source, khoảng 4 phút, cần gcc/g++). Nhóm `llama` của repo chưa có phần phụ thuộc của server, nên notebook khởi động server
bằng `uv run --with "starlette-context==0.5.1" python -m llama_cpp.server ...` (tải gói nhỏ đó vào một môi trường tạm, không
sửa `pyproject.toml`; lệnh kiểm ở mục `run` phía trên). Server chỉ nghe trên `127.0.0.1`, ở một cổng trống, và được tắt trong
`finally`. Nếu kernel chết giữa chừng mà server còn chạy nền: `pgrep -af llama_cpp.server` để kiểm, `pkill -f llama_cpp.server`
để dọn.

Mở `starter/loadtest.ipynb`, viết các cell chấm điểm theo mô tả trong notebook:

1. `parse_sse_line`, `stream_chat` (async; ghi thời điểm từng token, `usage`, lỗi HTTP và lỗi kết nối mà không ném ra).
2. `poisson_arrivals`, `run_open_loop` (theo lịch, có giới hạn đồng thời phía client), `run_closed_loop`.
3. `summarize` (thông lượng, TTFT, E2E, inter-token, hàng đợi, thời gian phục vụ theo phân vị).

Rồi chạy các cell `explore` theo thứ tự: server mặc định với 1 và 2 request đồng thời, server với `--interrupt_requests
false` ở 1, 2, 4, 8, Ollama cùng model, open loop ở ba mức tải (0.4, 0.75 và 1.0 lần công suất ước từ thời gian phục vụ
đo được), và prefix cache có/không `--cache`. Trả lời các câu ở cuối
notebook, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `parse_sse_line` xử lý dòng dữ liệu, `[DONE]`, comment, dòng trống, JSON hỏng.
- `stream_chat` trên server SSE giả: đúng số token (chunk `role`, chunk rỗng, `usage` và mọi thứ sau `[DONE]` không phải
  token), thời điểm token ghi lúc nhận, `usage` được lưu, payload gửi đi có `stream: true`; lỗi HTTP 503 và đứt kết nối giữa
  chừng thành bản ghi lỗi, không ném ra.
- `run_open_loop` gửi đúng lịch, xếp hàng phía client khi có giới hạn đồng thời (request thứ k chờ k lần thời gian phục
  vụ), trả kết quả theo thứ tự chỉ số; `run_closed_loop` giữ đúng số request trong hệ thống và gửi mỗi chỉ số một lần.
- `summarize` đúng mọi phân vị trên bản ghi tự dựng, loại request lỗi khỏi phân vị.
- Notebook lời giải chạy hết với llama.cpp server và Ollama thật.

## Gợi ý

### Gợi ý 1

Test dùng `httpx.MockTransport` với một async generator làm body, nên `stream_chat` phải đọc bằng
`client.stream(...)` và `aiter_lines()`, không đọc cả body một lần (đọc cả body thì mọi token có cùng thời điểm). Bọc cả
khối `async with` trong `try` để lỗi giữa stream cũng thành bản ghi.

### Gợi ý 2

Trong `run_open_loop`, tính thời điểm đến tuyệt đối `t0 + arrivals[i]` một lần rồi ngủ tới đó; đừng ngủ theo khoảng cách
giữa hai request liên tiếp (sai số cộng dồn). Giới hạn đồng thời đặt **sau** khi ngủ tới lịch: thời gian chờ semaphore là
hàng đợi bạn muốn đo. `asyncio.gather` giữ thứ tự kết quả theo thứ tự coroutine truyền vào.
