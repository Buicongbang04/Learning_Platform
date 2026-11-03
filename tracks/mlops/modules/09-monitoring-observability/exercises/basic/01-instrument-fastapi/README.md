---
title: Instrument service ETA bằng prometheus_client
level: basic
services: []
files:
  - path: starter/app.py
    note: Khai báo metric, middleware và endpoint /metrics (TODO)
  - path: tests/test_instrument.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/basic/01-instrument-fastapi -q
---

## Mục tiêu

Làm cho một service FastAPI "nói" được với Prometheus: đủ số liệu RED (Rate, Errors, Duration) cộng ba metric riêng của model,
mà không tạo ra thứ làm Prometheus chết dần là label có vô số giá trị.

## Đề bài

`starter/app.py` đã có service ETA chạy được (`POST /predict`, `GET /health`) nhưng chưa có số đo nào. Hoàn thiện `create_app`
sao cho `GET /metrics` trả định dạng text của Prometheus (`text/plain`) với các metric dưới đây. Mỗi lần gọi `create_app()`
tạo một `CollectorRegistry` riêng; không dùng registry toàn cục, vì test dựng nhiều app trong một tiến trình.

| Metric | Loại | Label | Ghi chú |
| --- | --- | --- | --- |
| `http_requests_total` | Counter | `method`, `route`, `status` | `status` là mã HTTP dạng chuỗi (`"200"`, `"422"`, `"500"`) |
| `http_request_duration_seconds` | Histogram | `method`, `route` | bucket đúng `LATENCY_BUCKETS` trong starter |
| `eta_prediction_seconds` | Histogram | không | quan sát mỗi `eta_seconds` trả về (kể cả khi dùng heuristic); bucket đúng `PREDICTION_BUCKETS` |
| `eta_fallback_total` | Counter | không | tăng mỗi lần `model.predict` ném `ModelError` và service dùng heuristic |
| `eta_model_info` | Info | `version` | giá trị `1`, `version` lấy từ `model.version`, đặt lúc tạo app |

Luật mà test kiểm:

- `route` là **mẫu đường dẫn** (`/predict`, `/health`), không phải URL thật. Đường dẫn không khớp route nào (404) có `route="unmatched"`.
  Tập `route` chỉ được phép là `/predict`, `/health`, `unmatched` (dùng sẵn `KNOWN_ROUTES`).
- Tên label chỉ được nằm trong `method`, `route`, `status`, `version` (cộng `le` do histogram tự sinh). Header `X-Request-ID`
  không bao giờ xuất hiện trong `/metrics`, dưới bất kỳ dạng nào.
- Lỗi 5xx do exception trong handler vẫn phải được đếm với `status="500"` và client vẫn nhận 500. Yêu cầu không hợp lệ
  (422) cũng được đếm.
- `/metrics` không tự đo chính nó: không có series `route="/metrics"`.
- Hai app tạo cùng tiến trình không dùng chung số đếm.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/basic/01-instrument-fastapi -q` pass.
- Gửi 40 yêu cầu tới 40 đường dẫn ngẫu nhiên không làm tăng số series của `http_requests_total` quá 6.
- Bạn giải thích được vì sao `route` an toàn còn `request_id` thì không (mỗi giá trị label là một chuỗi thời gian mới).

## Gợi ý

### Gợi ý 1

Middleware `@app.middleware("http")` thấy cả yêu cầu thành công lẫn lỗi. Sau khi `call_next` chạy xong, FastAPI đã gắn route
khớp vào `request.scope["route"]` (có thuộc tính `path` là mẫu). Không có route thì không có thuộc tính đó.

### Gợi ý 2

Tên counter trong `prometheus_client` không cần hậu tố: `Counter("http_requests", ...)` tự xuất `http_requests_total`, và
`Info("eta_model", ...)` xuất `eta_model_info`. Bọc `call_next` trong `try/except Exception` để vẫn đếm được 500, rồi trả
`JSONResponse(..., status_code=500)`.
