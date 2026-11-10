---
title: Ước tính chi phí GPU - giờ GPU, spot và hiệu suất scale
level: basic
services: []
files:
  - path: prices.yaml
    note: Bảng giá minh hoạ (ngày 2026-11-04), không sửa
  - path: starter/cost.py
    note: 7 hàm TODO
  - path: tests/test_cost.py
    note: Không sửa
  - path: quiz.yaml
    note: Trắc nghiệm chọn cách song song và công cụ
run:
  - uv run pytest tracks/mlops/modules/15-distributed-training/exercises/basic/03-gpu-cost-estimate -q
---

## Mục tiêu

Trả lời "job này tốn bao nhiêu và xong khi nào" bằng số trước khi thuê GPU: đổi giờ GPU của một card sang thời gian đồng hồ và tiền
theo số GPU, hiệu suất scale, on-demand hay spot, rồi chọn phương án rẻ nhất kịp deadline. Sau đó làm phần trắc nghiệm về các cách
song song và công cụ.

## Đề bài

`prices.yaml` là bảng giá **minh hoạ** (USD mỗi giờ GPU, làm tròn từ bảng giá công khai, ghi ngày 2026-11-04; giá thật đổi theo vùng,
cam kết và thời điểm). `spot: null` nghĩa là không có giá spot. Điền 7 hàm trong `starter/cost.py`, công thức là mô hình đơn giản hoá có
chủ ý (README module mục 5 và 7):

- **`load_prices(path)`**: trả `{gpu: {"on_demand": float, "spot": float | None}}`. `ValueError` khi: không có mục `gpus` hoặc rỗng;
  `on_demand` thiếu, không phải số (chuỗi `'3.2'` cũng không được) hoặc không dương; `spot` không phải `null` mà không phải số dương.
- **`scaling_efficiency(throughput_1, throughput_n, n)`** $$= \frac{T_n}{n \cdot T_1}$$.
- **`wall_hours(single_gpu_hours, n_gpus, efficiency)`** $$= \frac{H_1}{n \cdot e}$$. `ValueError` khi `n_gpus < 1` hoặc `efficiency` ngoài
  $$(0, 1]$$.
- **`spot_overhead_hours(hours, preemptions_per_hour, checkpoint_every_h, restart_h)`**: số lần bị thu hồi kỳ vọng
  `hours x preemptions_per_hour`, mỗi lần mất trung bình nửa khoảng checkpoint cộng thời gian khởi động lại:
  `hours x preemptions_per_hour x (checkpoint_every_h / 2 + restart_h)`.
- **`estimate(prices, gpu, n_gpus, single_gpu_hours, efficiency, market="on_demand", preemptions_per_hour=0, checkpoint_every_h=1, restart_h=0)`**
  trả `{"wall_hours", "gpu_hours", "cost"}`:
  - `wall_hours = wall_hours(...)`; nếu `market == "spot"` cộng thêm `spot_overhead_hours(wall_hours, ...)`.
  - `gpu_hours = wall_hours x n_gpus`, `cost = gpu_hours x giá của market đó`.
  - `ValueError` khi GPU không có trong bảng, `market` không phải `"on_demand"`/`"spot"`, hoặc giá của market đó là `None`.
- **`cheapest(prices, plans, deadline_h)`**: mỗi phương án là dict có `name` và các tham số của `estimate`. Bỏ phương án `estimate` báo
  `ValueError` và phương án có `wall_hours > deadline_h`; trả `{"name", "wall_hours", "gpu_hours", "cost"}` của phương án rẻ nhất (hoà
  thì chọn `wall_hours` nhỏ hơn); không còn phương án nào thì `None`.
- **`optimal_checkpoint_every_h(checkpoint_cost_h, preemptions_per_hour)`**: công thức Young
  $$\tau = \sqrt{2 \delta / \lambda}$$ (với $$M = 1/\lambda$$); `preemptions_per_hour <= 0` thì `math.inf`.

Test dùng bảng giá trong `prices.yaml` (bằng một bản chép sẵn, không đọc qua hàm của bạn trừ test của `load_prices`) và sáu phương án
cho một job: A100 x8 on-demand và spot, H100 x8 on-demand và spot, T4 x8 spot (không có giá), L4 x16 on-demand (quá chậm). Sau khi test
pass, làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/15-distributed-training/exercises/basic/03-gpu-cost-estimate -q` pass.
- Bạn giải thích được vì sao thêm GPU làm job xong sớm hơn mà không làm nó rẻ hơn.
- Bạn nêu được khi nào spot rẻ hơn trên giấy mà vẫn nên chọn on-demand.

## Gợi ý

### Gợi ý 1

`isinstance(True, int)` là `True` trong Python: kiểm `bool` riêng nếu muốn loại `on_demand: true`.

### Gợi ý 2

Trong `cheapest`, gọi `estimate(prices, **{k: v for k, v in plan.items() if k != "name"})` trong `try`, rồi
`min(..., key=lambda r: (r["cost"], r["wall_hours"]))`.
