---
title: Ngân sách độ trễ - TTFT, decode và percentile qua pipeline
level: basic
services: []
files:
  - path: starter/latency.py
    note: 6 hàm TODO
  - path: tests/test_latency.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/21-ai-system-design/exercises/basic/03-latency-budget -q
---

## Mục tiêu

Chia độ trễ của một request LLM thành các phần đo được (chờ, prefill, decode), biết trần tốc độ decode đến từ đâu,
và tính p95 của cả pipeline cho đúng. Làm xong bạn trả lời được "SLO 3 giây thì trả lời dài được bao nhiêu token" và
không cộng p95 của từng bước để ra p95 tổng.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/latency.py`, chỉ dùng thư viện chuẩn, theo quy ước ở mục 4 lý thuyết:

1. `ttft(prompt_tokens, prefill_tok_s, overhead_s=0.0) -> float`: thời gian tới token đầu
   $$\text{TTFT} = \text{overhead} + \frac{\text{prompt\_tokens}}{\text{prefill\_tok\_s}}$$. `overhead_s` gồm mạng, hàng
   đợi, guardrail. `ValueError` nếu `prompt_tokens < 0`, `prefill_tok_s <= 0` hoặc `overhead_s < 0`.
2. `e2e_latency(prompt_tokens, output_tokens, prefill_tok_s, decode_tok_s, overhead_s=0.0) -> float`:
   $$\text{TTFT} + \frac{\text{output\_tokens}}{\text{decode\_tok\_s}}$$. `ValueError` nếu `output_tokens < 0` hoặc
   `decode_tok_s <= 0`.
3. `decode_upper_bound_tok_s(bytes_per_token, bandwidth_bytes_s) -> float`: trần tốc độ decode khi batch 1, mỗi token
   phải đọc `bytes_per_token` byte (cỡ toàn bộ trọng số) từ bộ nhớ GPU có băng thông `bandwidth_bytes_s`.
   `ValueError` nếu đối số không dương.
4. `percentile(samples, q) -> float`: percentile `q` (0 tới 100) theo **nội suy tuyến tính** giữa hai phần tử kề nhau
   của mẫu đã sắp xếp, tức vị trí $$(n - 1)\frac{q}{100}$$ (khớp `numpy.percentile` mặc định). Không giả định `samples`
   đã sắp xếp. `ValueError` nếu rỗng hoặc `q` ngoài [0, 100].
5. `pipeline_percentiles(stage_samples, q) -> tuple[float, float]`: các bước chạy nối tiếp; `stage_samples[s][i]` là
   thời gian bước `s` của request `i`. Trả **(percentile q của tổng thời gian từng request, tổng các percentile q của
   từng bước)**. `ValueError` nếu không có bước nào hoặc các bước có số request khác nhau.
6. `max_output_tokens(budget_s, prompt_tokens, prefill_tok_s, decode_tok_s, overhead_s=0.0) -> int`: số token output
   tối đa để E2E không vượt `budget_s` (làm tròn xuống); 0 nếu TTFT đã vượt. Cẩn thận sai số dấu phẩy động ở đúng
   biên: ngân sách vừa khít 9 token phải ra 9, không phải 8.

## Tiêu chí đạt

- TTFT và E2E khớp giá trị tính tay; ví dụ 2 000 token prompt, 300 token output: 12.2 s, trong đó decode 10 s.
- Trần decode của `qwen2.5:3b` Q4_K_M (1 929 912 432 byte) trên 192 GB/s khoảng 99.5 token/s.
- `percentile` khớp `numpy.percentile` trên mẫu ngẫu nhiên nhiều cỡ và nhiều `q`.
- `pipeline_percentiles` cho thấy cả hai chiều: tổng các p80 thấp hơn p80 thật khi đuôi rơi vào các request khác nhau,
  và tổng các p95 cao hơn p95 thật khi các bước độc lập.
- `max_output_tokens` đúng ở biên và trả `int`.

## Gợi ý

### Gợi ý 1

`percentile`: sắp xếp, tính `pos = (n - 1) * q / 100`, lấy `lo = floor(pos)`, `hi = min(lo + 1, n - 1)`, nội suy theo
phần lẻ. Với `pipeline_percentiles`, `zip(*stage_samples.values())` cho bạn từng request theo hàng.

### Gợi ý 2

`max_output_tokens`: phần ngân sách còn lại nhân `decode_tok_s` có thể ra 8.999999999999995 vì $$2.5 - 2.2$$ trong
dấu phẩy động là 0.2999999999999998. Cộng một epsilon nhỏ (ví dụ `1e-9`) trước khi `floor`.
