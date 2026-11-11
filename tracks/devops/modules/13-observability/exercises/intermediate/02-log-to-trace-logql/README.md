---
title: Truy một request từ log tới trace bằng LogQL
level: intermediate
services: []
files:
  - path: starter/queries.yaml
    note: 4 query LogQL
  - path: tests/test_logql.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/13-observability/exercises/intermediate/02-log-to-trace-logql -q -rs
---

## Mục tiêu

Dùng LogQL như lúc trực sự cố: từ một `request_id` khách gửi kèm khiếu nại, tìm đúng log của request đó, lấy `trace_id`, mở trace trong
Jaeger, rồi đi tiếp sang log của worker trong cùng trace. Cuối cùng đếm lỗi từ log bằng metric query.

## Đề bài

Log của Olist Shop tới Loki qua OTLP. Mỗi dòng là JSON, ví dụ một dòng của API:

```json
{"ts": "2026-11-11T09:12:03.120+00:00", "level": "INFO", "msg": "request", "request_id": "chk-7", "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "logger": "olist_shop.api", "method": "GET", "path": "/orders/{order_id}", "status": 404, "duration_ms": 7.8}
```

- Nhãn stream: `service_name` (`olist-shop-api`, `olist-shop-worker`), `service_instance_id`.
- `trace_id`, `span_id` và các trường thêm của log (`method`, `path`, `status`...) cũng có trong **structured metadata**: lọc được bằng
  `| trace_id = "..."` mà không cần parser.
- API: mỗi request một dòng `msg="request"`; `POST /jobs/recompute` có thêm dòng `job enqueued`. Header `X-Request-ID` của client thành
  `request_id`.
- Worker: `request_id` của dòng log worker là `job_id`, **không** phải request id của client. Thứ nối API với worker là `trace_id`
  (context đi qua payload job trong Redis).

Viết bốn query trong `starter/queries.yaml`. Test thay `$request_id`, `$trace_id` bằng giá trị thật rồi gửi query tới Loki.

| Khoá | Kết quả cần |
| --- | --- |
| `request_logs` | Mọi dòng log của **API** có `request_id` **đúng bằng** `$request_id` (không khớp request khác có id chứa chuỗi đó) |
| `trace_id_of_request` | Mỗi dòng kết quả **chỉ là** `trace_id` 32 ký tự hex của request `$request_id` (dùng `line_format`) |
| `worker_logs_of_trace` | Log của **worker** thuộc trace `$trace_id` |
| `errors_by_path` | Metric query: số dòng log request trả 5xx trong 5 phút, gộp theo `path` (chỉ còn nhãn `path`) |

**Cách test chấm.** Test dựng Olist Shop cùng `ObsStack` một lần cho cả bài, gửi `GET /orders/...` với ba request id gần giống nhau,
một `POST /jobs/recompute` với `X-Request-ID: chk-job`, rồi dừng Redis và gọi `/readyz` (503) bốn lần. Sau đó:

| Test | Kiểm |
| --- | --- |
| `test_request_logs_match_exact_request_id` | Với `chk-7`: chỉ log của API, chỉ đúng request đó |
| `test_trace_id_of_request_leads_to_jaeger_trace` | Với `chk-77`: đúng một `trace_id`, và Jaeger có trace đó với span HTTP mang `olist.request_id=chk-77` |
| `test_follow_job_from_api_log_to_worker_log` | Từ `chk-job` lấy `trace_id`, rồi `worker_logs_of_trace` ra log worker của trace đó, có dòng `job done` |
| `test_errors_by_path` | Đỉnh của `/readyz` đúng 4; không có `/orders/{order_id}` (404 không phải 5xx) |

Lần đầu build image cần mạng; stack khoảng 30 giây, RAM khoảng 650 MB. Thử query nhanh hơn bằng tay: chạy stack theo
`setup/DEVOPS-TOOLS.md` mục "Stack observability", mở Grafana `Explore → Loki`, hoặc dùng `logcli` (mục 0 của module).

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao `|= "chk-7"` không đủ, và chi phí của `| json` so với line filter.
- Nói được vì sao `request_id` không đi được từ API sang worker còn `trace_id` thì đi được.

## Gợi ý

### Gợi ý 1

Thứ tự trong một query LogQL: stream selector `{...}` (chọn chunk, rẻ) → line filter `|=` (lọc chuỗi, rẻ) → parser `| json` (tách trường
thành label) → label filter `| request_id = "..."` (so đúng giá trị) → `| line_format "{{.trace_id}}"` (viết lại dòng). Đặt line filter
trước parser để Loki parse ít dòng hơn.

### Gợi ý 2

Metric query bọc log query trong một hàm theo khoảng: `count_over_time({...} | json | ... [5m])`, rồi `sum by (path) (...)`. Lọc số bằng
label filter như `status >= 500`. Một request có thể sinh nhiều dòng log; chỉ đếm dòng `msg="request"`.
