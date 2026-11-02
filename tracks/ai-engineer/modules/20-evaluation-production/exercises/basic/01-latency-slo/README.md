---
title: Độ trễ, khoảng tin cậy của p95, chi phí và SLO
level: basic
services: []
files:
  - path: starter/latency.py
    note: 5 hàm TODO
  - path: tests/test_latency.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/20-evaluation-production/exercises/basic/01-latency-slo -q
---

## Mục tiêu

Viết bộ hàm mà mọi báo cáo độ trễ và chi phí của một dịch vụ LLM cần: tách thời gian xếp hàng khỏi thời gian phục vụ,
đặt khoảng tin cậy cho p95 thay vì báo một con số trần, đọc phân vị từ histogram của hệ thống metrics, tính chi phí cho
1 000 request khi có token đọc từ cache, và đo một SLO bằng error budget. Bài tiếp nối module 21 (bài Basic 03 viết
`percentile` và ngân sách độ trễ); ở đây được dùng `numpy.percentile`.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/latency.py` (giữ nguyên dataclass `Request`):

1. `breakdown(req) -> dict`. `req.t_arrival` là lúc request đến hệ thống, `req.t_start` là lúc server bắt đầu xử lý
   (rời hàng đợi), `req.token_times` là thời điểm client nhận từng token. Trả:
   - `queue_s` = `t_start - t_arrival`; `ttft_s` = token đầu trừ `t_arrival`; `service_ttft_s` = token đầu trừ `t_start`;
   - `e2e_s` = token cuối trừ `t_arrival`;
   - `tpot_s` = (token cuối − token đầu) / (số token − 1), bằng `0.0` khi chỉ có một token;
   - `itl_s`: list khoảng cách giữa hai token liên tiếp (inter-token latency); `n_tokens`.

   `ValueError` khi không có token, khi không có `t_arrival <= t_start <= token đầu`, hoặc `token_times` giảm.
2. `bootstrap_percentile_ci(samples, q, n_boot=2000, seed=0, level=0.95) -> (point, lo, hi)`: `point` là
   `np.percentile(samples, q)`. Khoảng tin cậy theo bootstrap phân vị, làm **đúng thứ tự** này để số của bạn khớp test:
   `rng = np.random.default_rng(seed)`; `idx = rng.integers(0, n, size=(n_boot, n))`; thống kê của mỗi lần lấy mẫu lại là
   `np.percentile(x[idx], q, axis=1)`; `lo`, `hi` là phân vị $$100\cdot\frac{1-\text{level}}{2}$$ và
   $$100\cdot\left(1-\frac{1-\text{level}}{2}\right)$$ của các thống kê đó. Trả ba `float`. `ValueError` khi ít hơn 2 mẫu,
   `q` ngoài [0, 100] hoặc `level` ngoài (0, 1).
3. `histogram_quantile(bounds, cumulative_counts, q) -> float`, như hàm cùng tên của Prometheus: `bounds` là cận trên
   (`le`) tăng hẳn của các bucket, có thể kết thúc bằng `math.inf`; `cumulative_counts[i]` là số quan sát `<= bounds[i]`.
   Với hạng $$r = q \cdot N$$ ($$N$$ là tổng), tìm bucket đầu tiên có số đếm tích luỹ $$\ge r$$ rồi nội suy tuyến tính
   trong bucket đó, cận dưới của bucket đầu là 0. Rơi vào bucket `+Inf` thì trả cận trên hữu hạn lớn nhất. Tổng bằng 0
   thì `nan`. `ValueError` khi độ dài lệch, `bounds` không tăng hẳn, số đếm giảm, hoặc `q` ngoài [0, 1].
4. `cost_per_1k(usages, prices) -> float`: mỗi usage là dict `input_tokens`, `output_tokens`, tuỳ chọn `cached_tokens`
   (mặc định 0). Theo quy ước của OpenAI, `cached_tokens` là **một phần** của `input_tokens`. `prices` có `input`,
   `cached_input`, `output` tính USD mỗi triệu token. Trả chi phí trung bình mỗi request nhân 1 000. `ValueError` khi
   danh sách rỗng, số âm, hoặc `cached_tokens > input_tokens`.
5. `slo_report(latencies, ok, threshold_s, target) -> dict`: một request **tốt** khi `ok` và độ trễ `<= threshold_s`
   (request lỗi luôn xấu). Trả `n`, `good_ratio`, `bad` (số request xấu), `error_budget` = `1 - target`, `burn_rate` =
   tỉ lệ xấu chia error budget, `met` = `good_ratio >= target`. `ValueError` khi độ dài lệch, rỗng, hoặc `target` ngoài
   (0, 1).

## Tiêu chí đạt

- `breakdown` đúng ví dụ tính tay của test (TTFT 1.0 s gồm 0.5 s xếp hàng, TPOT 0.2 s) và từ chối thời điểm sai thứ tự.
- `bootstrap_percentile_ci` khớp định nghĩa trên từng chữ số, cùng `seed` cho cùng kết quả, khoảng 80% nằm trong khoảng
  95%, và trên 300 mẫu cỡ 200 từ phân phối mũ, khoảng 95% chứa p95 thật trong 85% tới 99% số lần.
- `histogram_quantile` khớp ba ví dụ tính tay, xử lý bucket `+Inf` và histogram rỗng, sai khác dưới 0.01 với phân vị
  thật trên 100 000 mẫu đều.
- `cost_per_1k` tính đúng khi có token cache; `slo_report` đúng burn rate 3.0 trong ví dụ và đúng ở biên `target`.

## Gợi ý

### Gợi ý 1

`x[idx]` với `idx` hai chiều cho ma trận `n_boot × n` mẫu lấy lại trong một phép, không cần vòng lặp Python. Với
histogram, viết ra giấy ví dụ đầu của test: 100 quan sát, hạng 50 nằm giữa số đếm 40 và 80 của bucket `(0.25, 0.5]`.

### Gợi ý 2

Trong `slo_report`, cộng điều kiện "lỗi" và "chậm" thành một mặt nạ boolean trước khi đếm. Burn rate 1 nghĩa là tiêu
đúng hết error budget trong cửa sổ đo; burn rate 3 nghĩa là với tốc độ này ngân sách hết sau một phần ba cửa sổ.
