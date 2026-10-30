# Lời giải: ngân sách độ trễ

## Cách làm

- `ttft`, `e2e_latency`: đúng công thức của đề, kiểm đối số trước.
- `decode_upper_bound_tok_s`: `bandwidth / bytes_per_token`.
- `percentile`: sắp xếp, vị trí $$(n-1)q/100$$, nội suy giữa `xs[lo]` và `xs[hi]`.
- `pipeline_percentiles`: tổng theo từng request bằng `zip(*stage_samples.values())`, rồi lấy percentile của tổng;
  song song tính tổng các percentile từng bước.
- `max_output_tokens`: `floor((budget - ttft) * decode_tok_s + 1e-9)`, 0 nếu phần còn lại không dương.

## Đọc kết quả

**Decode chiếm phần lớn độ trễ.** Ví dụ trong test: 2 000 token prompt ở 1 000 token/s prefill là 2 s, nhưng 300 token
output ở 30 token/s là 10 s. Prefill xử lý cả prompt song song (bị chặn bởi FLOPs), decode sinh từng token và mỗi
token phải đọc lại toàn bộ trọng số (bị chặn bởi băng thông bộ nhớ). Vì thế giảm độ dài **output** (yêu cầu trả lời
ngắn, structured output) thường hiệu quả hơn cắt prompt, và streaming quan trọng: người dùng thấy chữ sau TTFT chứ
không phải sau E2E.

**Trần decode.** `qwen2.5:3b` Q4_K_M nặng 1.93 GB; trên GPU 192 GB/s, batch 1 không thể nhanh hơn khoảng 99.5
token/s, dù GPU còn thừa FLOPs. Batch nhiều request dùng chung một lần đọc trọng số, nên thông lượng tổng tăng gần
tuyến tính cho tới khi chạm giới hạn compute hoặc bộ nhớ KV (bài Basic 02, Intermediate 01).

**p95 của tổng không phải tổng các p95.** Pipeline 3 bước độc lập trong test (guardrail, retrieval, LLM, 2 000
request lognormal, seed 42):

| | p50 | p95 | p99 |
| --- | --- | --- | --- |
| Percentile của tổng từng request | 1.96 s | 6.52 s | 11.46 s |
| Tổng percentile từng bước | 1.87 s | 6.97 s | 12.63 s |

Bước LLM có p95 6.29 s, retrieval 0.50 s, guardrail 0.18 s. Với các bước độc lập, request chậm ở bước này hiếm khi cũng
chậm ở bước kia, nên cộng p95 **đánh giá cao** đuôi (ước lượng bi quan, tốn tài nguyên). Ngược lại, ở test thứ nhất
đuôi của hai bước rơi vào hai request khác nhau và cộng p80 cho 5.6 s trong khi p80 thật là 11 s: **đánh giá thấp**.
Khi các bước tương quan dương (cùng chậm vì máy quá tải), cộng percentile gần đúng hơn. Không có công thức chung: đo
E2E của từng request (trace có span cho mỗi bước, module 20) rồi lấy percentile.

**Ngân sách token.** SLO 3 s, prompt 2 000 token, overhead 0.2 s: chỉ còn 24 token output ở 30 token/s, gần như không
trả lời được gì. Phải stream (SLO áp lên TTFT thay vì E2E), hoặc dùng model/GPU decode nhanh hơn.

## Bẫy thường gặp

- Tính percentile kiểu nearest-rank (`xs[int(q/100*n)]`) rồi so với numpy: khác ở mẫu nhỏ.
- Quên sắp xếp `samples`.
- Lấy trung bình độ trễ làm SLO: trung bình che đuôi, và người dùng nhớ lần chậm nhất.
- Không có epsilon trong `max_output_tokens`: mất một token ở đúng biên.
