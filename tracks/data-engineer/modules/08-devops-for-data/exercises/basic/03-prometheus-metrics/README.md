---
title: Xuất metric pipeline theo định dạng Prometheus
level: basic
services: []
files:
  - path: starter/metrics.py
    note: 3 TODO
  - path: tests/test_prometheus_metrics.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/basic/03-prometheus-metrics -q
---

## Mục tiêu

Hiểu định dạng text exposition của Prometheus (HELP, TYPE, label, counter, gauge) và tính được
metric freshness của một pipeline, bằng code thuần không cần thư viện.

## Đề bài

Sau mỗi lần chạy, các pipeline Olist (`orders`, `payments`…) ghi lại thống kê dạng:

```python
stats = [
    {"pipeline": "orders", "rows_processed": 98666, "last_success": 1730102400.0, "duration_seconds": 42.5},
    {"pipeline": "payments", "rows_processed": 103886, "last_success": 1730098800.0, "duration_seconds": 12.0},
]
```

Hoàn thiện ba hàm trong `starter/metrics.py`:

1. `escape_label_value(value: str) -> str`: thoát ký tự trong giá trị label theo chuẩn Prometheus:
   `\` thành `\\`, `"` thành `\"`, xuống dòng thành `\n`.
2. `render_metrics(stats: list[dict]) -> str`: trả về văn bản gồm ba metric family, theo thứ tự:
   - `pipeline_rows_processed_total` (counter), HELP `Rows processed by the pipeline.`
   - `pipeline_last_success_timestamp_seconds` (gauge), HELP `Unix time of the last successful run.`
   - `pipeline_duration_seconds` (gauge), HELP `Duration of the last run in seconds.`

   Mỗi family có đúng một dòng `# HELP <tên> <mô tả>` và một dòng `# TYPE <tên> <loại>`, rồi một dòng
   mẫu cho mỗi pipeline: `<tên>{pipeline="<giá trị đã escape>"} <số>`. Văn bản kết thúc bằng `\n`.
   Danh sách rỗng trả về chuỗi rỗng.
3. `freshness_seconds(now, last_success) -> float`: số giây từ lần thành công gần nhất tới `now`.
   Cả hai có thể là số (Unix seconds) hoặc `datetime` có timezone. `last_success is None` (chưa từng
   chạy thành công) trả về `float("inf")`. Kết quả không âm (đồng hồ lệch thì trả 0).

## Tiêu chí đạt

- Escape đúng `\`, `"` và xuống dòng.
- Mỗi metric family có HELP và TYPE đúng, đứng trước các dòng mẫu của nó.
- Có một dòng mẫu cho mỗi pipeline với đúng giá trị.
- Văn bản parse được bằng `prometheus_client.parser` (test này skip nếu thiếu thư viện).
- `freshness_seconds` đúng với số, với `datetime`, với `None`, và không âm.

## Gợi ý

### Gợi ý 1

Escape `\` trước, rồi mới tới `"` và `\n`; làm ngược lại sẽ escape hai lần dấu `\` vừa thêm.

### Gợi ý 2

Khai báo các family trong một list `[(tên, loại, help, khoá trong dict), ...]`, lặp qua từng family
rồi lặp qua `stats` bên trong. Với `datetime`, dùng `.timestamp()`.
