---
title: Máy tính chi phí inference và chọn model theo ràng buộc
level: basic
services: []
files:
  - path: starter/cost.py
    note: 4 hàm TODO
  - path: tests/test_cost.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/00-introduction/exercises/basic/01-inference-cost -q
---

## Mục tiêu

Viết thành code phép tính mà AI Engineer phải làm trước mỗi quyết định chọn model: một request tốn bao nhiêu, một
tháng tốn bao nhiêu khi có prompt cache, tự host thì mỗi triệu token giá bao nhiêu, và model rẻ nhất nào vẫn đạt chất
lượng và độ trễ yêu cầu.

## Đề bài

**Phần cứng:** CPU · ~40 phút

Đọc mục 5 lý thuyết trước. Giá tính bằng **USD cho mỗi triệu token** (USD/MTok); định dạng bảng giá (dict, có thể có
`cached_input` và `long_context`) mô tả ở đầu `starter/cost.py`. Giá trong test là **giá giả định**, không phải giá
thật của nhà cung cấp nào.

Trong `starter/cost.py`, chỉ dùng thư viện chuẩn, viết:

1. `request_cost(n_in, n_out, price, n_cached=0) -> float`: chi phí một request theo công thức ở mục 5. `n_cached` là
   **một phần** của `n_in` (token đọc từ prompt cache, tính giá `cached_input`; bảng giá không có `cached_input` thì
   tính giá `input`). Có `long_context` và `n_in > threshold` thì **cả request** (mọi token input, cache, output) tính
   theo bảng giá con, như cách tính của Claude Haiku 5.5 và Gemini 2.5 Pro. Số token âm hoặc `n_cached > n_in` thì
   `ValueError`.
2. `monthly_cost(requests_per_day, n_in, n_out, price, cache_hit=0.0, days=30) -> float`: chi phí `days` ngày;
   `cache_hit` là tỉ lệ token input đọc từ cache, ngoài `[0, 1]` thì `ValueError`. Không làm tròn số token cache: đây
   là kỳ vọng trên nhiều request.
3. `self_hosted_cost_per_mtok(gpu_usd_per_hour, tokens_per_s, utilization=1.0) -> float`: công thức tự host ở mục 5.
   Tham số không dương hoặc `utilization > 1` thì `ValueError`.
4. `choose_model(candidates, n_in, n_out, requests_per_day, min_quality, max_latency_s) -> str | None`: trong các ứng
   viên đạt `quality >= min_quality` và độ trễ ước lượng `ttft_s + n_out / tokens_per_s <= max_latency_s`, trả tên
   ứng viên có `monthly_cost` (không cache) nhỏ nhất; bằng nhau thì ứng viên đứng trước; không ai đạt thì `None`.

Làm xong, tự trả lời bằng hàm của bạn với giá thật trong bảng mục 5: một chatbot 10 000 request mỗi ngày, mỗi request
2 000 token input và 500 token output, tốn bao nhiêu mỗi tháng với Claude Sonnet 5.5 và với gpt-6-luna? Nếu 1 500 token
đầu của prompt là system prompt cố định đọc từ cache thì giảm bao nhiêu phần trăm?

## Tiêu chí đạt

- `request_cost(2000, 500, {"input": 4, "output": 20, ...}) == 0.018`; thêm `n_cached=1500` với `cached_input` 0.2 thì
  0.0123.
- Prompt đúng bằng ngưỡng `long_context` tính giá thường, vượt 1 token thì cả request tính giá dài.
- `monthly_cost` khớp tính tay khi có `cache_hit`, kể cả khi số token cache không nguyên.
- `self_hosted_cost_per_mtok(1.0, 1000, 0.3)` khoảng 0.926 (số ở mục 5 lý thuyết).
- `choose_model` lọc đúng cả chất lượng lẫn độ trễ (bằng ngưỡng vẫn đạt), dùng giá `long_context` khi prompt dài, giữ
  ứng viên đứng trước khi bằng chi phí.
- Mọi đầu vào sai trong đề bài ném `ValueError`.

## Gợi ý

### Gợi ý 1

Viết một hàm phụ nhận `(n_in, n_out, price, n_cached)` **không** kiểm đầu vào, chỉ chọn bảng giá (thường hay dài) rồi
tính. `request_cost` kiểm đầu vào rồi gọi nó; `monthly_cost` gọi nó với `n_cached = n_in * cache_hit` (số thực) rồi
nhân số request. Chọn bảng giá theo `n_in` tổng, không theo phần không cache.

### Gợi ý 2

`price.get("long_context")` trả `None` khi không có khoá. Giá cache lấy bằng `tier.get("cached_input", tier["input"])`
trên **bảng giá đã chọn**. Trong `choose_model`, giữ `(tên, chi phí)` tốt nhất và chỉ thay khi chi phí **nhỏ hơn hẳn**.
