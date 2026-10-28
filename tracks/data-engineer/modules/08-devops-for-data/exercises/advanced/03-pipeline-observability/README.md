---
title: Bộ giám sát pipeline - freshness, volume anomaly, p95 latency, error rate
level: advanced
services: []
files:
  - path: starter/monitor.py
    note: Hiện thực PipelineMonitor theo đặc tả
  - path: tests/test_pipeline_observability.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/advanced/03-pipeline-observability -q
---

## Mục tiêu

Tự xây phần lõi của một hệ thống data observability: từ lịch sử các lần chạy, tính các metric
vận hành quan trọng (freshness, volume, latency, error rate), sinh cảnh báo có ý nghĩa và xuất
metric cho Prometheus.

## Đề bài

Các pipeline Olist (`orders`, `payments`, `reviews`) sau mỗi lần chạy gửi một `Run` (đã định nghĩa
trong `starter/monitor.py`): `pipeline`, `started_at` (Unix seconds), `duration_seconds`, `rows`,
`status` (`"success"` hoặc `"failed"`). Thời điểm kết thúc là `started_at + duration_seconds`.

Hiện thực lớp `PipelineMonitor(freshness_sla, z_threshold=3.0, min_history=5,
error_rate_threshold=0.2, error_window=20, p95_threshold=None)`:

- `freshness_sla`: dict `pipeline -> số giây tối đa` kể từ lần thành công gần nhất.
- `p95_threshold`: dict `pipeline -> giây` hoặc `None` (không cảnh báo latency).

Các phương thức:

| Phương thức | Đặc tả |
| --- | --- |
| `record(run)` | Lưu một lần chạy. Run có thể tới không theo thứ tự thời gian. |
| `last_success(pipeline)` | Thời điểm **kết thúc** muộn nhất của run thành công, `None` nếu chưa có. |
| `freshness(pipeline, now)` | `now - last_success`, không âm; `math.inf` nếu chưa từng thành công. |
| `p95_duration(pipeline)` | p95 theo **nearest-rank** trên `duration_seconds` của mọi run: sắp tăng dần, lấy phần tử thứ `ceil(0.95 * n)` (đếm từ 1). `None` nếu chưa có run. |
| `error_rate(pipeline)` | Tỉ lệ `failed` trong `error_window` run **gần nhất** (theo `started_at`). `0.0` nếu chưa có run. |
| `volume_zscore(pipeline)` | Xét các run thành công theo `started_at`. Run mới nhất so với **mọi** run thành công trước nó: `(x - mean) / pstdev`. `None` nếu số run trước đó `< min_history`. Nếu `pstdev == 0`: trả `0.0` khi `x == mean`, ngược lại `±math.inf` theo dấu. |
| `evaluate(now)` | Danh sách `Alert(pipeline, kind, message)` sắp theo `(pipeline, kind)`. Xét mọi pipeline có trong `freshness_sla` hoặc đã `record`. `kind` gồm: `"freshness"` (pipeline có SLA và `freshness > SLA`), `"volume"` (`abs(z) > z_threshold`), `"error_rate"` (`error_rate > error_rate_threshold`), `"latency"` (có ngưỡng và `p95 > ngưỡng`). |
| `to_prometheus(now)` | Văn bản Prometheus exposition, các family bên dưới, mỗi family có `# HELP` và `# TYPE`, kết thúc bằng `\n`. |

Metric cần xuất (label `pipeline`, giá trị label cần escape `\`, `"`, xuống dòng):

- `pipeline_freshness_seconds` (gauge), `+Inf` nếu chưa từng thành công.
- `pipeline_runs_total` (counter), thêm label `status` (`success`/`failed`), chỉ xuất cặp đã có run.
- `pipeline_duration_p95_seconds` (gauge), chỉ pipeline có run.
- `pipeline_last_run_rows` (gauge): `rows` của run mới nhất (theo `started_at`).

Gợi ý tình huống thực: Olist ngày thường có ~3.000 đơn/giờ; một lần chạy chỉ nạp 120 đơn (nguồn
bị lỗi một phần) phải bị bắt bằng volume anomaly dù job vẫn `success`.

## Tiêu chí đạt

- Mọi phương thức đúng đặc tả kể cả trường hợp biên (chưa có run, run lộn thứ tự, pstdev = 0).
- `evaluate` bắn đúng loại cảnh báo, không bắn nhầm khi mọi thứ bình thường.
- `to_prometheus` parse được bằng `prometheus_client.parser` (test skip nếu thiếu thư viện) và có
  giá trị đúng.
- Code rõ ràng, có thể giải thích lựa chọn ngưỡng và cách tránh alert fatigue (xem SOLUTION.md).

## Gợi ý

### Gợi ý 1

Lưu run theo `dict[str, list[Run]]` và sắp theo `started_at` khi cần. Dùng `statistics.mean`,
`statistics.pstdev`, `math.ceil`.

### Gợi ý 2

Z-score chỉ đáng tin khi lịch sử đủ dài (`min_history`). Thực tế nên so với cùng khung giờ/ngày
trong tuần (seasonality); bài này dùng phiên bản đơn giản.
