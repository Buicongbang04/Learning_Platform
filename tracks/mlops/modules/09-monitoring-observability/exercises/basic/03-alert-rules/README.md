---
title: Viết rule alert và kiểm bằng promtool test rules
level: basic
services: []
files:
  - path: starter/rules.yml
    note: Viết hai alert (đang rỗng)
  - path: tests/test_rules.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/basic/03-alert-rules -q
---

## Mục tiêu

Viết hai alert theo triệu chứng cho service ETA và chứng minh chúng đúng bằng `promtool test rules`: bắn khi người dùng
thật sự bị ảnh hưởng, im lặng khi không có traffic, và kêu khi chính số đo biến mất.

## Đề bài

Trong `starter/rules.yml` viết hai alert (promtool chạy trong container `prom/prometheus:v3.5.0` qua `mlopskit.promtool`,
không cần stack). Dữ liệu mà service ETA xuất ra có nhãn `job="eta-service"`, `method`, `route`, `status` như bài 01: metric
`http_requests_total`, `status` là mã HTTP (`"200"`, `"500"`...).

| Alert | Điều kiện | `for` | `severity` |
| --- | --- | --- | --- |
| `ETAHighErrorRate` | Tỉ lệ yêu cầu `route="/predict"` trả 5xx vượt **5%**, tính trên cửa sổ 5 phút, gộp mọi series (`sum`) | từ 3m tới 10m | `critical` |
| `ETAMetricsAbsent` | Không còn series `http_requests_total{job="eta-service"}` nào | từ 1m tới 10m | `warning` |

Luật mà test kiểm:

- Tên alert đúng như bảng, không trùng tên; file qua `promtool check rules`.
- Mỗi alert có `annotations.summary` không rỗng và `annotations.runbook_url` bắt đầu bằng `https://`.
- Alert lỗi chỉ xét route `/predict`: lỗi 5xx ở `/health` không được làm nó bắn.
- **Không có traffic** (mọi bộ đếm đứng yên ở 0, dù series vẫn tồn tại) thì **không** bắn `ETAHighErrorRate` và cũng không bắn
  `ETAMetricsAbsent`.
- Lỗi 1% không bắn. Lỗi 10% kéo dài: chưa bắn ở phút thứ 2, bắn ở phút 15 và 30. Lỗi dừng lại thì alert tự hết.
- Khi series biến mất hẳn (stale), `ETAMetricsAbsent` bắn trước phút 25 và `ETAHighErrorRate` không bắn.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/basic/03-alert-rules -q` pass.
- Bạn giải thích được vì sao alert theo triệu chứng (tỉ lệ lỗi của người dùng) tốt hơn alert theo nguyên nhân (CPU cao),
  và vì sao `for` quan trọng.
- Bạn nêu được điều gì xảy ra khi `rate(...)` chia cho `rate(...)` mà mẫu số bằng 0.

## Gợi ý

### Gợi ý 1

Tỉ lệ lỗi là `sum(rate(lỗi[5m])) / sum(rate(tất cả[5m]))`. Chọn lỗi bằng regex trên `status`: `status=~"5.."`. Cả tử và mẫu
đều phải lọc cùng `job` và `route`.

### Gợi ý 2

`promtool test rules` đọc `input_series` dạng `a+bxN` (bắt đầu từ `a`, mỗi phút cộng `b`, `N` lần). Hãy xem test để thấy cách
dùng `ALERTS{alertname=..., alertstate="firing"}` kiểm một alert đang bắn. `absent(vector)` trả 1 khi vector rỗng.
