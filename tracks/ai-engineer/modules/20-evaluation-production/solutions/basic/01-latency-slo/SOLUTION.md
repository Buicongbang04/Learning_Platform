# Lời giải: độ trễ, khoảng tin cậy của p95, chi phí và SLO

## Cách làm

- `breakdown`: kiểm thứ tự thời điểm trước rồi mới trừ. `ttft_s` tính từ `t_arrival` (người dùng thấy cả hàng đợi), còn
  `service_ttft_s` tính từ `t_start` (phần server thật sự làm). Tách hai số này là việc đầu tiên khi TTFT xấu đi: nếu
  `service_ttft_s` đứng yên mà `ttft_s` tăng thì vấn đề là hàng đợi (thiếu replica, thiếu batching), không phải model.
- `bootstrap_percentile_ci`: một ma trận chỉ số `n_boot × n` rồi `np.percentile(x[idx], q, axis=1)`; không vòng lặp Python.
  Khoảng là phân vị của các thống kê lấy lại (percentile bootstrap).
- `histogram_quantile`: hạng $$r = qN$$, bucket đầu có số đếm tích luỹ $$\ge r$$, nội suy tuyến tính giữa cận dưới và cận
  trên của bucket đó theo phần hạng còn lại; bucket `+Inf` không nội suy được nên trả cận hữu hạn lớn nhất, đúng như
  Prometheus.
- `cost_per_1k`: `cached_tokens` là tập con của `input_tokens` (quy ước OpenAI); Anthropic báo `cache_read_input_tokens`
  **riêng** khỏi `input_tokens`, nên khi đọc usage của Anthropic phải cộng lại trước khi dùng hàm này.
- `slo_report`: một mặt nạ `ok & (lat <= threshold)`; burn rate là tỉ lệ xấu chia error budget.

## Vì sao như vậy

- **Khoảng tin cậy cho phân vị đuôi** là thứ hay bị bỏ nhất. Trên 40 request open loop của một lượt đo thử theo thiết lập bài Intermediate 02 (rate 0.8),
  bootstrap cho E2E p95 9.44 s [7.71, 9.97] và p99 9.78 s [8.94, 9.97]: cận trên của cả hai là request chậm nhất. Với
  $$n$$ mẫu, p99 chỉ có nghĩa khi $$n$$ cỡ vài nghìn; báo p99 trên vài chục request là báo một mẫu.
- Bootstrap phân vị hơi **hẹp** ở đuôi với mẫu nhỏ (nó không thể tạo giá trị lớn hơn max). Test kiểm độ phủ trên phân phối
  mũ với $$n = 200$$: khoảng 95% chứa p95 thật trong 85% tới 99% số lần, không đòi đúng 95%.
- **Histogram** là cách mọi hệ thống metric lưu độ trễ. Trên 120 request của lượt đo thử đó với bucket 0.25, 0.5, 1,
  2.5, 5, 10 giây, `histogram_quantile` cho p95 8.42 s so với 7.71 s thật: bucket (5, 10] quá rộng. Đặt ranh giới bucket
  dày quanh ngưỡng SLO.
- **Burn rate** trả lời "với tốc độ này, bao lâu nữa hết ngân sách": burn rate 3 trên cửa sổ 28 ngày nghĩa là hết ngân sách
  sau khoảng 9 ngày.

## Lỗi hay gặp

- Tính TTFT từ `t_start` rồi gọi đó là độ trễ người dùng thấy.
- Lấy mẫu bootstrap không hoàn lại (`rng.permutation`): mọi lần lấy lại là cùng một tập, khoảng tin cậy co về một điểm.
- Trừ `cached_tokens` hai lần, hoặc cộng cả `input_tokens` lẫn `cached_tokens` với giá đầy đủ.
- Bỏ request lỗi khỏi SLO vì "không có độ trễ": request lỗi luôn là request xấu.
- So sánh phân vị bằng `>` với `threshold` (`<=` là tốt): ở đúng biên, cả SLO đổi kết quả.
