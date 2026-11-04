---
title: Tính bốn SLI của ML, error budget và burn rate từ log sự kiện
level: basic
services: []
files:
  - path: starter/slo.py
    note: 8 hàm TODO
  - path: tests/test_slo.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/basic/01-sli-error-budget -q
---

## Mục tiêu

Tự tay tính bốn SLI của một service ML (khả dụng, độ trễ, chất lượng, freshness), quy SLO ra error budget và burn rate. Làm bằng
Python thuần trên log để chắc chắn bạn hiểu từng mẫu số trước khi viết nó bằng PromQL.

## Đề bài

Mỗi sự kiện là một dict (test sinh một ngày log của service ETA, mỗi 10 giây một yêu cầu, giờ cuối có sự cố):

| Khoá | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `ts` | `int` | giây kể từ đầu ngày |
| `status` | `int` | mã HTTP trả cho client |
| `latency_ms` | `float` | thời gian trả lời |
| `abs_error_min` | `float` hoặc `None` | sai số tuyệt đối (phút) khi nhãn đã về; `None` khi chưa có nhãn |
| `feature_age_s` | `float` | tuổi của feature dùng cho dự đoán này (giây) |

Điền 8 hàm trong `starter/slo.py`:

- `availability(events)`: tỉ lệ sự kiện có `status < 500`.
- `latency_sli(events, threshold_ms)`: **chỉ xét sự kiện có `status < 500`**, tỉ lệ có `latency_ms <= threshold_ms`.
- `quality_sli(events, tolerance_min)`: **chỉ xét sự kiện đã có nhãn**, tỉ lệ có `abs_error_min <= tolerance_min`.
- `freshness_sli(events, max_age_s)`: tỉ lệ sự kiện có `feature_age_s <= max_age_s`.
- Bốn hàm trên trả `None` khi mẫu số bằng 0 (không có sự kiện nào thuộc diện xét). Mọi ngưỡng so sánh `<=`.
- `budget_minutes(slo, window_days)`: `(1 - slo) x window_days x 1440`.
- `error_budget(sli, slo, total)`: dict `allowed_bad = (1 - slo) x total`, `bad = (1 - sli) x total`,
  `remaining = 1 - bad / allowed_bad` (âm khi đã tiêu quá budget).
- `burn_rate(bad_ratio, slo)`: `bad_ratio / (1 - slo)`.
- `window_burn_rates(events, slo, now, windows_s)`: với mỗi cửa sổ `w` (giây) trong `windows_s`, lấy sự kiện có
  `now - w <= ts < now` và tính burn rate của **khả dụng** (`bad_ratio = 1 - availability`); cửa sổ không có sự kiện cho `0.0`.
  Trả dict `{w: burn_rate}`.

Test so với giá trị tự tính bằng numpy trên cùng log (sai số `pytest.approx`).

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/basic/01-sli-error-budget -q` pass.
- Bạn giải thích được vì sao latency SLI bỏ các yêu cầu lỗi khỏi mẫu số, và vì sao quality SLI không có nhãn thì là `None`
  chứ không phải 1.0.
- Bạn tự tính được: SLO 99.5% trong 30 ngày cho 216 phút budget; burn rate 14.4 trong 1 giờ tiêu 2% budget.

## Gợi ý

### Gợi ý 1

Viết một hàm phụ `ratio(good, total)` trả `None` khi `total == 0`, rồi bốn hàm SLI chỉ còn là chọn mẫu số và tử số.

### Gợi ý 2

`window_burn_rates` gọi lại `availability` trên các sự kiện trong cửa sổ rồi `burn_rate(1 - value, slo)`. Cửa sổ là nửa mở: sự kiện
đúng tại `now` thuộc cửa sổ sau.
