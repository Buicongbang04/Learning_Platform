---
title: Ước tính chi phí hằng tháng cho kịch bản train và serve từ bảng giá YAML
level: basic
services: []
files:
  - path: starter/prices.yaml
    note: Bảng giá minh hoạ, không sửa
  - path: starter/cost.py
    note: 3 hàm TODO
  - path: tests/test_cost.py
    note: Không sửa
  - path: tests/fixtures/prices.yaml
    note: Bản gốc bảng giá, không sửa
run:
  - uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/basic/03-ml-cost-estimate -q
---

## Mục tiêu

Trước khi xin ngân sách hay chọn giữa tự dựng và dịch vụ cloud, phải ước được hoá đơn tháng. Bạn viết bộ ước tính từ một bảng giá và một kịch bản, tách **train** (trả theo lần chạy) khỏi **serve** (trả theo giờ treo máy, kể cả lúc rảnh), và đo phần tiền bỏ vào máy nhàn rỗi.

## Đề bài

`starter/prices.yaml` là bảng giá minh hoạ (không phải giá thật của nhà cung cấp nào; luôn kiểm bảng giá hiện hành trước khi quyết định). Kịch bản là một dict:

```yaml
train: {instance: gpu.g5.xlarge, hours_per_run: 3, runs_per_month: 8, spot: true}
serve: {instance: cpu.m5.xlarge, replicas: 2, utilization: 0.15, scale_to_zero: false, committed: false}
storage_gb: 500
egress_gb: 200
```

Trong `starter/cost.py`:

1. `estimate(scenario, prices) -> dict` với các khoá `train`, `serve`, `idle_serve`, `storage`, `egress`, `total` (số `float`, mỗi số làm tròn 2 chữ số thập phân; `total` là tổng các thành phần **chưa làm tròn** rồi mới làm tròn; `idle_serve` là một phần của `serve`, không cộng thêm vào `total`).
   - `train = giá_giờ × hours_per_run × runs_per_month`, nhân `spot_multiplier` khi `spot` là `true`.
   - `serve = giá_giờ × replicas × giờ_tính_tiền`, nhân `committed_multiplier` khi `committed` là `true`. `giờ_tính_tiền` là `hours_per_month` khi `scale_to_zero` là `false`, và `hours_per_month × utilization` khi `true`.
   - `idle_serve = serve × (1 - utilization)` khi `scale_to_zero` là `false`, và `0` khi `true` (máy không chạy thì không có tiền nhàn rỗi).
   - `storage = storage_gb × storage_gb_month`; `egress = egress_gb × egress_gb`.
2. `idle_share(est) -> float`: `idle_serve / total`, làm tròn 4 chữ số; `0.0` khi `total` bằng 0.
3. `savings(scenario, prices, **overrides) -> dict`: áp `overrides` lên một **bản sao** của kịch bản (khoá `serve`, `train`, `storage_gb`, `egress_gb`; với `serve` và `train` chỉ cập nhật các khoá được truyền, không thay cả dict) và trả `{"before": total_cũ, "after": total_mới, "saved": before - after}`, `saved` làm tròn 2 chữ số.

Luật mà test ép:

- Instance không có trong bảng giá thì `ValueError` nêu tên instance; `utilization` ngoài `[0, 1]` hoặc `replicas`, `runs_per_month` âm thì `ValueError`.
- Không sửa kịch bản hay bảng giá được truyền vào (`savings` không làm đổi dict gốc).
- Kết quả là số cụ thể trong test; sai một hệ số là fail.

## Tiêu chí đạt

- Test pass.
- Chỉ ra được trong kịch bản mẫu thành phần nào chiếm hoá đơn và vì sao train GPU rẻ hơn serve CPU ở đây.
- Nêu được hai cách giảm tiền nhàn rỗi và đánh đổi của từng cách (độ trễ khởi động nguội, cam kết dài hạn).

## Gợi ý

### Gợi ý 1

Tính từng thành phần thành `float` thô, giữ nguyên đến lúc cộng `total`. Làm tròn từng thành phần rồi cộng có thể lệch 1 cent so với test.

### Gợi ý 2

`copy.deepcopy(scenario)` rồi `update` cho `train` và `serve` bằng các dict con được truyền; so sánh `before` và `after` qua cùng một hàm `estimate`.
