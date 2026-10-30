---
title: Đo độ trễ inference thật với Ollama - prefill, decode, TTFT
level: intermediate
services: []
files:
  - path: starter/latency.ipynb
    note: 5 hàm TODO
  - path: tests/test_latency.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/00-introduction/exercises/intermediate/02-inference-latency/starter/latency.ipynb
  - uv run pytest tracks/ai-engineer/modules/00-introduction/exercises/intermediate/02-inference-latency -q
---

## Mục tiêu

Tự đo hai pha của inference mà mục 4 lý thuyết mô tả: prefill nhanh, decode chậm, cold start, và thấy độ trễ dao động
thế nào khi máy bận. Dựng một mô hình độ trễ tuyến tính từ phép đo của chính bạn để dự đoán độ trễ của một tính năng
trước khi xây nó, và báo cáo bằng p50, p95 thay vì một con số.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Cần Ollama với `qwen2.5:3b` (Ollama tự dùng GPU nếu có; số liệu trong lời giải đo trên RTX 3050 Laptop 4GB). Các cell
`explore` gửi khoảng 25 request, chạy 2 tới 5 phút khi GPU rảnh, lâu hơn nhiều nếu GPU đang bận việc khác.

Mở `starter/latency.ipynb`. Trong các cell chấm điểm viết:

1. `ollama_metrics(resp) -> dict`: đọc các trường thời gian (nano giây) trong response của `/api/chat`, trả số token,
   thời gian từng pha (giây), tốc độ prefill và decode (token/giây), và `ttft_s = load_s + prefill_s`. Trường thiếu coi
   là 0; thời gian bằng 0 thì tốc độ là `0.0`.
2. `summarize(values) -> dict`: `n`, `mean`, `p50`, `p95`, `max` (phân vị nội suy tuyến tính).
3. `fit_latency(n_in, n_out, total_s) -> dict`: bình phương tối thiểu $$T \approx a + b\,n_{in} + c\,n_{out}$$, trả `a`, `b`,
   `c`, `r2`.
4. `predict_latency(model, n_in, n_out) -> float`.
5. `stream_timing(t_send, chunk_times) -> dict`: TTFT, độ trễ toàn phần và TPOT đo phía client khi stream.

Rồi chạy các cell `explore`: lần gọi đầu (cold start), quét độ dài prompt (điều luật Zalo Legal cắt ở 200 tới 9 000 ký
tự) và độ dài output (16, 64, 256 token), tách thời gian phục vụ (`load + prefill + decode`) khỏi thời gian chờ hàng
đợi, khớp mô hình trên thời gian phục vụ, đo stream, và dự đoán độ trễ của một câu trả lời RAG. Trả lời
các câu ở cuối notebook, sau đó làm phần trắc nghiệm của bài trong app. Số đo của bạn sẽ khác lời giải; các câu trắc
nghiệm hỏi về quan hệ giữa các con số, đúng trên mọi máy có GPU.

## Tiêu chí đạt

- `ollama_metrics` trên hai response thật trong test (cold và warm) cho đúng 74.05 token/giây decode, cold start 4.83
  giây; xử lý trường thiếu và thời gian 0.
- `summarize` khớp `np.percentile`: p95 của `[1, 2, 3, 4, 10]` là 8.8; dãy rỗng báo `ValueError`.
- `fit_latency` khôi phục đúng hệ số trên dữ liệu tuyến tính chính xác và khớp `np.linalg.lstsq` trên dữ liệu có nhiễu;
  báo `ValueError` khi dưới 3 phép đo hoặc độ dài lệch.
- `stream_timing` đúng với một chunk và nhiều chunk.
- Cell `explore` chạy hết với Ollama thật và in bảng quét, hệ số mô hình, p50/p95 của TTFT và TPOT.

## Gợi ý

### Gợi ý 1

`resp.get("load_duration", 0)` cho trường thiếu. Phân vị: `np.percentile(x, 95)` mặc định nội suy tuyến tính. Với
`fit_latency`, dựng ma trận thiết kế ba cột `[1, n_in, n_out]` bằng `np.column_stack`.

### Gợi ý 2

`np.linalg.lstsq(X, y, rcond=None)` trả nghiệm ở phần tử đầu. $$R^2$$ tính từ phần dư của chính nghiệm đó. Trong
`stream_timing`, TPOT là khoảng cách trung bình giữa các chunk, nên dùng chunk đầu chứ không dùng `t_send` (khoảng từ
`t_send` tới chunk đầu là TTFT, không phải TPOT).
