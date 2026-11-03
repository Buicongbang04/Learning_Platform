---
title: Alert burn rate nhiều cửa sổ cho SLO chất lượng và freshness
level: intermediate
services: []
files:
  - path: starter/ml_slo.rules.yml
    note: Recording rule và 4 alert (đang rỗng)
  - path: tests/test_ml_slo_rules.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/intermediate/01-ml-slo-burn-rate-alerts -q
---

## Mục tiêu

Module 09 đã viết burn-rate cho SLO khả dụng. Bài này làm phần riêng của ML: SLO **chất lượng** (nhãn về muộn, thưa) và SLO
**freshness** (feature cũ dần theo thời gian, không phải theo số request). Bạn chọn cửa sổ hợp với từng loại SLI, và bắt cả
trường hợp SLO "xanh" chỉ vì không còn dữ liệu để đo.

## Đề bài

Viết `starter/ml_slo.rules.yml`. Test chạy `promtool check rules` và `promtool test rules` trong container `prom/prometheus:v3.5.0`
qua `mlopskit.promtool` (cần Docker, không cần stack).

Dữ liệu đầu vào:

- `eta_quality_checks_total{job="eta-service", model, outcome}`: counter, tăng mỗi khi job join nhãn chấm một dự đoán; `outcome="good"`
  khi sai số tuyệt đối không quá 10 phút, `"bad"` khi vượt. Nhãn về theo lô nên test cho counter tăng **mỗi 5 phút**.
- `eta_feature_last_success_timestamp_seconds{job="feature-pipeline", feature_view}`: gauge, Unix time (giây) của lần materialize
  thành công gần nhất. Chỉ `feature_view="trip_stats"` thuộc SLO này; view khác (vd. `zone_stats`) có thể cũ mà không được làm alert bắn.

SLO (cửa sổ 30 ngày):

| SLI | Định nghĩa | SLO |
| --- | --- | --- |
| Chất lượng | tỉ lệ `outcome="good"` trên tổng số lần chấm | 98% |
| Freshness | tỉ lệ thời gian (theo phút) mà tuổi của `trip_stats` không quá 900 giây | 99% |

Bốn alert phải có (tên đúng như bảng, không trùng tên):

| Alert | Điều kiện | `for` | `severity` |
| --- | --- | --- | --- |
| `ETAQualityBudgetFastBurn` | burn rate trên **6** ở cả cửa sổ `6h` và `30m` | tối đa 30m | `critical` |
| `ETAQualityBudgetSlowBurn` | burn rate trên **3** ở cả cửa sổ `1d` và `2h` | tối đa 1h | `warning` |
| `ETAQualityLabelsMissing` | không có lần chấm nào trong 6 giờ, **kể cả khi series biến mất hẳn** | tối đa 1h | `warning` |
| `ETAFeatureFreshnessFastBurn` | burn rate trên **14.4** ở cả cửa sổ `1h` và `5m` | tối đa 5m | `critical` |

Luật mà test kiểm:

- File qua `promtool check rules`. Mỗi alert có `annotations.summary` không rỗng, `annotations.runbook_url` bắt đầu bằng `https://`,
  `labels.severity` và `for` như bảng. Ba alert burn rate có biểu thức chứa `and` (hai cửa sổ).
- Promtool đánh giá rule mỗi phút (`evaluation_interval: 1m`).
- Chất lượng: 20% dự đoán tệ kéo dài thì `FastBurn` bắn ở giờ 12 và `SlowBurn` bắn ở giờ 30; 8% tệ chỉ `SlowBurn` bắn; 1.5% tệ không
  alert nào bắn. 20% tệ trong 12 giờ rồi về 0%: `FastBurn` bắn ở giờ 11 và **đã tắt** ở giờ 13.
- Nhãn ngừng về (counter đứng yên, hoặc series biến mất): `LabelsMissing` chưa bắn ở giờ 3, bắn ở giờ 14; hai alert burn rate chất
  lượng không bắn.
- Freshness: `trip_stats` ngừng cập nhật từ phút 60 tới phút 100 thì alert chưa bắn ở phút 70, bắn ở phút 97, tắt ở phút 120;
  ngừng từ phút 60 tới phút 78 (chỉ cũ quá 900 giây trong vài phút) thì không bắn; luôn tươi thì không bắn.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/intermediate/01-ml-slo-burn-rate-alerts -q` pass.
- Bạn giải thích được vì sao SLO chất lượng dùng cửa sổ dài hơn SLO khả dụng, và vì sao không có tầng 1h/5m cho chất lượng.
- Bạn nói được vì sao "không có nhãn" phải là một alert riêng chứ không để tỉ lệ chất lượng tự xử lý.

## Gợi ý

### Gợi ý 1

Ngưỡng của burn rate B với SLO S là tỉ lệ tệ `B x (1 - S)`: chất lượng `6 x 0.02 = 0.12`, freshness `14.4 x 0.01 = 0.144`. Viết hằng
số dạng `(6 * 0.02)` để người đọc thấy nguồn gốc. Tỉ lệ chất lượng là `sum(rate(bad[w])) / sum(rate(all[w]))`, mỗi cửa sổ một
recording rule (`eta:quality_bad_ratio:rate6h`...).

### Gợi ý 2

Freshness là SLI theo thời gian: mỗi phút "tươi" hay "cũ". `(time() - gauge) > bool 900` cho 1 khi cũ, 0 khi tươi; ghi nó thành
recording rule rồi `avg_over_time(...[1h])` là tỉ lệ thời gian cũ. Với nhãn biến mất: `sum(increase(...))` của vector rỗng là rỗng,
không phải 0; `or vector(0)` biến "không có gì" thành 0.
