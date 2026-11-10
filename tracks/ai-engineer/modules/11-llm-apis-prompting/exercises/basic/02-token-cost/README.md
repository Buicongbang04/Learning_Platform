---
title: Máy tính chi phí token, Batch API và điểm hoà vốn của prompt caching
level: basic
services: []
files:
  - path: starter/cost.py
    note: 4 hàm TODO
  - path: tests/test_cost.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/basic/02-token-cost -q
---

## Mục tiêu

Tự viết máy tính chi phí mà mọi quyết định "dùng model nào, có cache không, có chạy batch không" cần tới, và hiểu vì
sao prefix chung của prompt (system, few-shot, tài liệu) là chỗ tiết kiệm lớn nhất. Giá là tham số: code của bạn vẫn
đúng khi bảng giá đổi vào tháng sau.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/cost.py`, chỉ dùng thư viện chuẩn, viết bốn hàm theo công thức ở mục 3 lý thuyết. Giá tính bằng USD cho
mỗi triệu token (MTok):

1. `request_cost(usage, price, *, batch=False)`:
   $$C = \frac{n_{\text{in}} p_{\text{in}} + n_{\text{out}} p_{\text{out}} + n_{\text{cw}} p_{\text{cw}} + n_{\text{cr}} p_{\text{cr}}}{10^6}$$
   với `input_tokens` là token vào **không** thuộc cache. `batch=True` nhân cả tổng với `1 - price.batch_discount`.
   `ValueError` khi số token âm, hoặc có token ghi/đọc cache mà `Price` không có giá tương ứng (`None`).
2. `workload_cost(n_requests, prompt_tokens, output_tokens, price, *, cached_prefix_tokens=0, cache_hit_rate=0.0,
   batch=False)`: mỗi request có `prompt_tokens` token vào, trong đó `cached_prefix_tokens` đầu là prefix chung.
   Tỉ lệ `cache_hit_rate` request **đọc** prefix từ cache, phần còn lại **ghi** prefix vào cache; phần còn lại của
   prompt luôn là input thường. Trả chi phí kỳ vọng của cả workload. Tỉ lệ 0 hay 1 không được đòi giá của trường hợp
   không xảy ra.
3. `cache_breakeven(price)`: số lần đọc $$n$$ nhỏ nhất (số nguyên $$\ge 0$$) sau một lần ghi sao cho
   $$p_{\text{cw}} + n\,p_{\text{cr}} \le (1 + n)\,p_{\text{in}}$$. Ví dụ ghi 1.25 lần, đọc 0.1 lần giá input: hoà
   vốn sau 1 lần đọc; ghi 2 lần: sau 2 lần đọc.
4. `rank_models(prices, n_requests, prompt_tokens, output_tokens, **kwargs)`: xếp các model từ rẻ tới đắt cho cùng
   workload, hoà thì theo tên.

Test dùng bảng giá **giả định** (số tròn để tính tay), không phải giá thật. Sau khi test xanh, thử với bảng giá thật
ở mục 3 lý thuyết (đã kiểm ngày ghi ở đó, có thể đã đổi): một nghìn phản hồi sinh viên mỗi ngày, mỗi phản hồi một
lượt phân loại với prompt few-shot đo ở bài Intermediate 02, tốn bao nhiêu một tháng với từng model, có cache và
không cache.

## Tiêu chí đạt

- `request_cost` khớp tính tay khi có đủ bốn loại token, giảm đúng theo `batch_discount`, ném `ValueError` với
  token âm hoặc thiếu giá cache.
- `workload_cost` ra 600 USD cho 100 000 request (1 500 vào, 100 ra, giá $3/$15) và 317.4 USD khi 1 200 token đầu là
  prefix trúng cache 90% (ghi $3.75, đọc $0.30); tỉ lệ 0 không cần giá đọc cache.
- `cache_breakeven` cho 1, 2, 4, 0 ở bốn bảng giá của test, đúng biên (tỉ số nguyên không bị cộng thừa một).
- `rank_models` rẻ trước, hoà theo tên, truyền tiếp `batch` và tham số cache.

## Gợi ý

### Gợi ý 1

Viết `request_cost` trước, rồi `workload_cost` chỉ là trung bình có trọng số của hai `Usage`: một request trúng cache
và một request trượt. Chỉ tính nhánh nào có trọng số lớn hơn 0.

### Gợi ý 2

Biến đổi bất đẳng thức hoà vốn về dạng $$n \ge \frac{a}{b}$$ rồi lấy trần. Cẩn thận với số thực: $$\frac{2}{0.5}$$ có thể ra
4.000000000000001 và trần thành 5; trừ một lượng rất nhỏ trước khi lấy trần, hoặc so sánh bằng số nguyên khi có thể.
