---
title: Recording rule và alert rule cho API Olist Shop, kèm unit test bằng promtool
level: basic
services: []
files:
  - path: starter/rules.yml
    note: 3 recording rule, 2 alert
  - path: starter/rules.test.yml
    note: Unit test của bạn cho promtool
  - path: tests/test_rules.py
    note: Không sửa
  - path: tests/fixtures/semantics.test.yml
    note: Kịch bản kiểm đặc tả, không sửa
run:
  - uv run pytest tracks/devops/modules/13-observability/exercises/basic/01-recording-alert-rules -q -rs
---

## Mục tiêu

Viết recording rule đặt tên đúng quy ước `level:metric:operations`, viết alert theo triệu chứng dựa trên chúng, rồi tự chứng minh rule
đúng bằng `promtool test rules`: test của bạn phải đủ chặt để bắt được rule hỏng, và rule phải ra số với metric thật của Olist Shop.

## Đề bài

API Olist Shop xuất ở `/metrics` (scrape job `olist-api`):

- `http_requests_total{method, path, status}`: counter; `path` là route template (`/orders/{order_id}`), `status` là mã HTTP dạng
  chuỗi (`"200"`, `"404"`, `"503"`).
- `http_request_duration_seconds_bucket{method, path, le}` (cùng `_sum`, `_count`): histogram thời gian xử lý.

Prometheus gắn thêm `job` và `instance`.

**1. `starter/rules.yml`.**

| Tên | Loại | Yêu cầu |
| --- | --- | --- |
| `job:http_requests:rate5m` | record | Số request mỗi giây trên cửa sổ 5 phút, gộp theo `job` (chỉ còn nhãn `job`) |
| `job:http_requests_errors:ratio_rate5m` | record | Tỉ lệ request trả 5xx trên tổng request, cửa sổ 5 phút, gộp theo `job` |
| `job_path:http_request_duration_seconds:p95_5m` | record | p95 thời gian xử lý trên cửa sổ 5 phút, theo `job` và `path` (chỉ còn hai nhãn này) |
| `OlistApiHighErrorRate` | alert | Tỉ lệ 5xx của `job="olist-api"` vượt 5%; `for: 5m`; `labels.severity: page` |
| `OlistApiSlowOrders` | alert | p95 của `job="olist-api"`, `path="/orders/{order_id}"` vượt 0,5 giây; `for: 10m`; `labels.severity: ticket` |

Alert dùng recording rule, không viết lại biểu thức gốc. Mỗi alert có `annotations.summary` (nên dùng `{{ $value }}`) và
`annotations.runbook_url` bắt đầu bằng `https://`.

**2. `starter/rules.test.yml`**: unit test của bạn cho `promtool test rules`, `rule_files: [rules.yml]`.

- Có `promql_expr_test` cho cả ba recording rule, so đúng giá trị.
- Mỗi alert có ít nhất một ca **bắn** và một ca **không bắn**. Ca không bắn phải có dữ liệu (traffic khoẻ, request nhanh), không chỉ
  "không có series nào": ca đó luôn qua kể cả với rule hỏng.

**Cách test chấm.** `promtool` chạy trong container image `prom/prometheus` ghim (`testkit.promtool`), không cần cài.

| Test | Kiểm |
| --- | --- |
| `test_rules_pass_promtool_check` | `promtool check rules rules.yml` |
| `test_alert_labels_and_annotations` | `severity`, `summary`, `runbook_url` |
| `test_rules_behave_as_specified` | Chạy `tests/fixtures/semantics.test.yml` trên rule của bạn (đã bỏ annotations và mọi nhãn thêm của alert trừ `severity`, nên bạn được thêm nhãn như `team`): giá trị recording rule, nhãn còn lại, thời điểm alert bắn, không bắn khi lỗi 1%, khi job khác lỗi, khi không có traffic, khi path khác chậm |
| `test_own_unit_tests_pass_and_cover_every_rule` | `rules.test.yml` pass và phủ đủ như trên |
| `test_own_unit_tests_catch_broken_rule` (7 ca) | Test sửa rule của bạn thành bản hỏng (nhân đôi hay chia đôi giá trị, alert không bao giờ bắn, alert luôn bắn khi có dữ liệu); `rules.test.yml` phải **fail** với mỗi bản hỏng |
| `test_rules_on_real_olist_data` | Dựng Olist Shop cùng `ObsStack`, nạp `rules.yml` vào Prometheus, gửi request (có 503 thật), rồi kiểm Prometheus nạp rule không lỗi và cả ba recording rule ra số với `job="olist-api"` |

Test cuối build image Olist Shop (lần đầu cần mạng để `pip install`, khoảng 1 phút; sau đó dùng cache) và dựng stack (khoảng 40 giây,
RAM khoảng 650 MB). Thiếu image thì test skip kèm lệnh `docker pull`.

Tự chạy promtool khi làm bài, trong thư mục `starter/`:

```bash
docker run --rm --network none -u "$(id -u):$(id -g)" -v "$PWD:/work:ro" -w /work --entrypoint /bin/promtool \
  prom/prometheus:v3.5.0@sha256:63805ebb8d2b3920190daf1cb14a60871b16fd38bed42b857a3182bc621f4996 test rules rules.test.yml
```

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao `rate()` phải nằm **trong** `sum()`, và vì sao `histogram_quantile` cần giữ nhãn `le` khi gộp.
- Nói được alert sẽ ở trạng thái nào (inactive, pending, firing) ở phút thứ 3 và 12 của một đợt lỗi 25% kéo dài.

## Gợi ý

### Gợi ý 1

Thứ tự là `sum by (...) (rate(counter[5m]))`. Tỉ lệ lỗi là hai vế cùng `sum by (job)`, tử số lọc theo nhãn mã HTTP bằng regex `5..`.
p95: `histogram_quantile(0.95, sum by (job, path, le) (rate(..._bucket[5m])))`.

### Gợi ý 2

Trong `rules.test.yml`, `values: '0+60x20'` là counter tăng 60 mỗi bước, tức 1 request/giây với `interval: 1m`. Với `for: 5m`, alert
cần dữ liệu ít nhất 1 phút để `rate` có hai mẫu, cộng 5 phút pending, nên kiểm ca bắn ở khoảng phút 10 trở đi. `exp_alerts` phải ghi đủ
nhãn và annotations sau khi điền mẫu (`promtool` so khớp chính xác). Histogram chỉ cần các bucket `le`; đặt mọi request vào bucket đầu
tiên thì p95 dễ tính: `0.95 × le`.
