---
title: Ollama qua REST API thô, stream và bẫy num_ctx
level: intermediate
services: []
files:
  - path: starter/ollama_rest.ipynb
    note: 5 hàm TODO
  - path: tests/test_ollama_rest.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - uv run python data/download_dataset.py wikipedia-vi
  - uv run jupyter lab tracks/ai-engineer/modules/09-llms-and-open-models/exercises/intermediate/02-ollama-rest/starter/ollama_rest.ipynb
  - uv run pytest tracks/ai-engineer/modules/09-llms-and-open-models/exercises/intermediate/02-ollama-rest -q
---

## Mục tiêu

Nói chuyện với Ollama không qua thư viện: dựng payload `/api/chat`, đọc stream NDJSON, tính TTFT và token/s từ thống
kê của server, đọc context length, quantization, giấy phép từ `/api/show`, viết Modelfile. Rồi tự tay gặp lỗi im lặng
phổ biến nhất khi chạy model local: prompt dài bị `num_ctx` cắt mất mà không có lỗi nào.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Cần Ollama đang chạy với `qwen2.5:3b` (GPU 4 GB giúp nhanh hơn nhưng không bắt buộc). Ngoài thời gian làm bài, các
cell `explore` gọi model khoảng 8 lần, trong đó 2 lần với prompt khoảng 6 000 token: trên laptop của track lúc máy
đang bận, cả notebook chạy khoảng «TBD-NBTIME» phút; máy rảnh nhanh hơn nhiều.

Mở `starter/ollama_rest.ipynb`. Trong cell chấm điểm:

1. `chat_payload(model, messages, *, stream, temperature, top_p, top_k, num_ctx, num_predict, seed, keep_alive,
   format)`: body `POST /api/chat`, option nào khác `None` mới gửi.
2. `parse_stream(lines)`: nối các mảnh `message.content`, trả kèm object `done: true`; báo lỗi khi server trả
   `error` hoặc stream đứt.
3. `speed_stats(final)`: thời gian load, số token và token/s của prompt và của phần sinh, tổng thời gian (từ nano giây).
4. `model_facts(show)`: kiến trúc, số tham số, context length, quantization, giấy phép từ `/api/show`.
5. `render_modelfile(base, system, parameters)`: Modelfile với `FROM`, `PARAMETER`, `SYSTEM`.

Rồi chạy các cell `explore`: liệt kê model và đọc thông tin `qwen2.5:3b`, `qwen2.5:7b`; stream một câu trả lời, đo
TTFT và token/s, xem `/api/ps`; so với `llmkit.chat` và endpoint `/v1/chat/completions`; thí nghiệm `num_ctx` với
prompt khoảng 6 000 token có dữ kiện ở đầu; tạo model con từ Modelfile, gọi thử, xoá. Sau đó làm phần trắc nghiệm
của bài trong app.

## Tiêu chí đạt

- `chat_payload`: đúng 3 khoá bắt buộc; option là `0` vẫn gửi; không có option thì không có khoá `options`;
  `keep_alive`, `format` ở cấp ngoài.
- `parse_stream`: nhận `str` và `bytes`, bỏ dòng rỗng, dừng ở `done: true`, `RuntimeError` khi có `error` hoặc thiếu
  `done`.
- `speed_stats`: đúng đơn vị (nano giây sang giây), trường thiếu coi là 0, không chia cho 0.
- `model_facts`: khoá context theo kiến trúc (`<architecture>.context_length`), giấy phép thiếu là `None`.
- `render_modelfile` khớp từng ký tự, giá trị list thành nhiều dòng `PARAMETER`.
- Cell `explore` chạy hết; bạn đọc được từ output vì sao câu trả lời ở `num_ctx` mặc định sai.

## Gợi ý

### Gợi ý 1

`httpx.Client.stream("POST", ...)` cùng `response.iter_lines()` trả từng dòng ngay khi server gửi: đo TTFT ở dòng đầu
tiên có `content` khác rỗng. Lọc option bằng `is not None`, không bằng truthiness: `temperature=0` và `keep_alive=0`
là giá trị có nghĩa (greedy, và "giải phóng model ngay").

### Gợi ý 2

So `prompt_eval_count` trong response với số token bạn ước lượng cho prompt (khoảng 3.5 ký tự tiếng Việt một token với
Qwen2.5, mục 4 lý thuyết). Nếu nó dừng đúng ở một số tròn như 4 096, prompt đã bị cắt. Đầu prompt bị cắt mất thì dữ
kiện đặt ở đầu biến mất.
