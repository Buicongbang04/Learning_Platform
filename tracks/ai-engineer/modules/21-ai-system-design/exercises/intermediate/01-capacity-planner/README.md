---
title: Máy tính capacity - từ SLO tới số GPU và điểm hoà vốn với API
level: intermediate
services: []
files:
  - path: starter/capacity.py
    note: 8 hàm TODO
  - path: tests/test_capacity.py
    note: Không sửa
  - path: tests/fixtures/bench_7b_1gpu.csv
    note: Benchmark GIẢ ĐỊNH một GPU (concurrency, TTFT p95, TPOT p95)
run:
  - uv run pytest tracks/ai-engineer/modules/21-ai-system-design/exercises/intermediate/01-capacity-planner -q
---

## Mục tiêu

Biến một bảng benchmark và một SLO thành số GPU cần thuê, rồi so với API để biết khi nào self-host đáng. Làm xong bạn
hiểu vì sao "GPU chạy được bao nhiêu request" không có một đáp số: nó phụ thuộc SLO, và nới SLO thêm vài giây có thể
giảm một nửa số GPU.

## Đề bài

**Phần cứng:** CPU · ~75 phút

`tests/fixtures/bench_7b_1gpu.csv` là bảng benchmark **giả định** của một model 7B trên một GPU, cùng dạng số mà
`vllm bench serve` in ra khi chạy ở nhiều mức concurrency (số request đồng thời): mỗi dòng có `concurrency`,
`ttft_p95_s` (giây) và `tpot_p95_s` (time per output token, giây mỗi token). Concurrency càng cao, mỗi request càng
chậm nhưng GPU phục vụ được nhiều request hơn mỗi giây. Một dòng benchmark là dict
`{"concurrency": int, "ttft_p95_s": float, "tpot_p95_s": float}`. Trong `starter/capacity.py`, chỉ dùng thư viện chuẩn:

1. `peak_rps(requests_per_day, peak_to_avg) -> float`: request/giây giờ cao điểm,
   $$\frac{\text{requests\_per\_day}}{86\,400} \cdot \text{peak\_to\_avg}$$. `ValueError` nếu số request âm hoặc hệ số < 1.
2. `little_concurrency(rps, latency_s) -> float`: định luật Little $$L = \lambda W$$. `ValueError` nếu âm.
3. `request_latency(row, output_tokens) -> float`: $$\text{TTFT}_{p95} + n_{out} \cdot \text{TPOT}_{p95}$$, xấp xỉ độ trễ p95
   ở điểm vận hành đó (cộng hai p95 là xấp xỉ bi quan, xem bài Basic 03).
4. `rps_per_gpu(row, output_tokens) -> float`: một GPU giữ `concurrency` request, mỗi cái mất `request_latency`, nên
   phục vụ $$\frac{c}{\text{latency}}$$ request/giây (định luật Little đảo lại).
5. `best_operating_point(bench, output_tokens, ttft_slo_s, e2e_slo_s) -> dict | None`: trong các dòng có
   `ttft_p95_s <= ttft_slo_s` **và** `request_latency <= e2e_slo_s`, chọn dòng có `rps_per_gpu` lớn nhất (bằng nhau
   thì concurrency nhỏ hơn); không dòng nào đạt thì `None`.
6. `gpus_needed(peak_rps, bench, output_tokens, ttft_slo_s, e2e_slo_s, headroom=0.2, redundancy=1) -> int`:
   $$\left\lceil \frac{\text{peak} \cdot (1 + \text{headroom})}{\text{rps\_per\_gpu}} \right\rceil + \text{redundancy}$$ ở điểm vận hành tốt nhất.
   `headroom` là phần dư cho lưu lượng tăng đột ngột, `redundancy` là GPU dự phòng khi một máy hỏng (N+1). Đúng biên
   (ví dụ 3.0) không được làm tròn thành 4. `ValueError` nếu không điểm nào đạt SLO hoặc đối số âm.
7. `self_host_monthly_usd(n_gpus, usd_per_gpu_hour, hours_per_month=730) -> float`: tiền thuê GPU chạy 24/7.
8. `break_even_requests_per_month(fixed_monthly_usd, api_cost_per_request, self_host_cost_per_request=0.0) -> float`:
   số request mỗi tháng mà từ đó self-host rẻ hơn API, $$\frac{\text{fixed}}{\text{api} - \text{self}}$$;
   `math.inf` nếu API không đắt hơn phần biến đổi của self-host.

Sau khi test xanh, làm phần trắc nghiệm của bài trong app. Câu hỏi dùng cùng bảng benchmark và SLO TTFT 1 s.

## Tiêu chí đạt

- Với 300 token output, SLO TTFT 1 s và E2E 10 s, điểm vận hành tốt nhất là concurrency 32 (3.575 request/giây mỗi
  GPU); E2E 6 s thì là concurrency 8.
- Điểm tốt nhất là thông lượng lớn nhất, không phải concurrency lớn nhất còn đạt SLO.
- 20 request/giây cao điểm cần 8 GPU với SLO E2E 10 s và 16 GPU với SLO 6 s (headroom 20%, N+1).
- Chi phí self-host, điểm hoà vốn và trường hợp không bao giờ hoà vốn đúng; đầu vào sai ném `ValueError`.

## Gợi ý

### Gợi ý 1

Viết `request_latency` và `rps_per_gpu` trước; `best_operating_point` chỉ là lọc theo hai SLO rồi `max` theo khoá
`(rps_per_gpu, -concurrency)`. In ra bảng `concurrency, latency, rps_per_gpu` cho 300 token output để nhìn thấy đánh
đổi: latency tăng đều, thông lượng tăng nhanh rồi chậm lại.

### Gợi ý 2

`math.ceil(24 / 8.0)` là 3, nhưng `math.ceil(0.1 * 3 / 0.1)` có thể ra 4 vì sai số dấu phẩy động. Trừ một epsilon nhỏ
trước khi `ceil`. Điểm hoà vốn: self-host có chi phí cố định (thuê GPU cả tháng dù không ai dùng) cộng chi phí biến
đổi nhỏ; API chỉ có chi phí biến đổi.
