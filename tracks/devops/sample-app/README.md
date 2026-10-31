# Olist Shop — ứng dụng mẫu của track DevOps

Olist Shop là app nhỏ mà mọi bài tập và capstone của track DevOps vận hành: đóng container, đặt Nginx phía
trước, đưa lên Kubernetes, gắn metrics/log/trace. Bạn **không** phải viết code ứng dụng; hãy coi nó như
một service do team khác giao cho bạn vận hành. Interface dưới đây là hợp đồng ổn định, các module sau
dựa vào nó.

```mermaid
flowchart LR
    client[Client / curl] -->|HTTP :28000| api[api - FastAPI]
    api -->|SQL| pg[(postgres:16)]
    api -->|RPUSH olist:jobs| redis[(redis:7)]
    worker[worker] -->|BLPOP olist:jobs| redis
    worker -->|tính revenue_by_state| pg
    seed[seed - chạy một lần] -->|nạp CSV Olist| pg
```

## Thành phần

| Thành phần | Mã nguồn | Việc |
| --- | --- | --- |
| API | `olist_shop/main.py` (`olist_shop.main:app`) | HTTP endpoint, metrics, log JSON |
| Worker | `olist_shop/worker.py` (`python -m olist_shop.worker`) | Lấy job từ Redis, tính doanh thu theo bang |
| Seed | `olist_shop/seed.py` (`python -m olist_shop.seed <thư mục CSV>`) | Nạp `orders`, `order_items`, `customers` |
| Cấu hình | `olist_shop/settings.py` | Đọc biến môi trường |
| Log | `olist_shop/log.py` | Log JSON một dòng mỗi sự kiện |

## Endpoint

| Method | Path | Trả về |
| --- | --- | --- |
| GET | `/healthz` | `200 {"status":"ok","version":APP_VERSION}`, không chạm DB/Redis (liveness) |
| GET | `/readyz` | `200 {"db":"ok","redis":"ok"}`; thành phần nào lỗi thì `503` và giá trị `"error"` (readiness) |
| GET | `/orders/{order_id}` | Đơn hàng, danh sách item, `total` = tổng `price + freight_value`; không có thì `404` |
| GET | `/stats/revenue-by-state` | `[{"state": "SP", "revenue": 123.45}, ...]` giảm dần, đọc bảng `revenue_by_state` do worker tính |
| POST | `/jobs/recompute` | Đẩy job `recompute_revenue` vào list Redis `olist:jobs`, trả `202 {"job_id": ...}` |
| GET | `/metrics` | Prometheus: `http_requests_total{method,path,status}`, `http_request_duration_seconds`, `jobs_enqueued_total` |

Nhãn `path` là route template (`/orders/{order_id}`), không phải URL thật; URL không khớp route nào gom
thành `path="unmatched"`. Nếu dùng URL thật, mỗi order id sinh một time series và Prometheus sẽ nổ
cardinality.

Worker phơi metrics `jobs_processed_total`, `jobs_failed_total` ở cổng `WORKER_METRICS_PORT` (mặc định
`9101`, chỉ trong mạng compose). Worker dùng `BLPOP` timeout 5 giây và thoát sạch khi nhận `SIGTERM`.

## Biến môi trường

| Biến | Mặc định | Ghi chú |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./olist_shop.db` | Compose đặt `postgresql+psycopg://olist:olist@postgres:5432/olist` |
| `REDIS_URL` | `redis://localhost:26379/0` | Compose đặt `redis://redis:6379/0` |
| `LOG_LEVEL` | `INFO` | |
| `APP_VERSION` | `dev` | Trả trong `/healthz`, dùng để kiểm bản đang chạy sau deploy |
| `WORKER_METRICS_PORT` | `9101` | Chỉ worker dùng |
| `OLIST_SHOP_PG_PORT` / `OLIST_SHOP_REDIS_PORT` / `OLIST_SHOP_API_PORT` | `25432` / `26379` / `28000` | Cổng trên máy host |
| `DEVOPS_CPUSET` | rỗng | Ghim core cho mọi container, ví dụ `12-35` trên máy dùng chung |

Cổng host cố ý tránh `5432`, `6379`, `8000`, `8080`, `9000`, `9001` và cả `15432`, `16379` (cổng mà
stack của track DE trong `setup/` hay được đổi sang) để không đụng project khác. Nếu vẫn trùng, sao chép
`.env.example` thành `.env` và đổi cổng.

`api` và `worker` có `restart: unless-stopped`. Lần đầu chạy trên volume mới, cả hai cùng tạo bảng; nếu
Postgres báo trùng bảng, worker thử lại vài lần, còn nếu vẫn chết thì Docker khởi động lại nó.

## Log

Mỗi sự kiện là một dòng JSON có `ts`, `level`, `msg`, `request_id`. API lấy `request_id` từ header
`X-Request-ID` (hoặc sinh mới) và trả lại trong header response, nên bạn lần được một request qua
Nginx, API và log. Ở worker, `request_id` là `job_id`.

```json
{"ts": "2026-11-01T08:00:00.000+00:00", "level": "INFO", "msg": "request", "request_id": "abc", "logger": "olist_shop.api", "method": "GET", "path": "/healthz", "status": 200, "duration_ms": 1.2}
```

## Chạy bằng Docker Compose

Các lệnh dưới chạy trong `tracks/devops/sample-app`. Compose đọc `DEVOPS_CPUSET` bạn đã `export` (xem [Ghim CPU](../README.md#ghim-cpu-trên-máy-dùng-chung)) để ghim core; để trống thì không ghim. Lệnh build hạ ưu tiên bằng `nice`:

```bash
cd tracks/devops/sample-app
nice -n 15 docker compose up -d --build
curl -s localhost:28000/readyz
```

Nạp dữ liệu. Nếu chưa có `data/raw/olist` (từ `data/download_olist.py`), sinh dữ liệu giả cùng schema:

```bash
uv run python ../../../data/generate_olist.py --orders 5000 --out /tmp/olist
DATABASE_URL=postgresql+psycopg://olist:olist@localhost:25432/olist \
  uv run python -m olist_shop.seed /tmp/olist --limit-orders 5000
```

Seed xoá dữ liệu cũ rồi nạp lại, chạy nhiều lần vẫn ra cùng kết quả. Tính doanh thu rồi xem kết quả:

```bash
curl -s -X POST localhost:28000/jobs/recompute
curl -s localhost:28000/stats/revenue-by-state
docker compose logs worker
```

Dọn sạch khi xong (xoá cả volume Postgres):

```bash
docker compose down -v
```

`Dockerfile` ở đây cố ý đơn giản (một stage, chạy bằng root). Module 06 sẽ yêu cầu bạn viết lại nó.

## Test

Test không cần Docker: dùng SQLite tạm và `fakeredis`, dữ liệu là vài dòng CSV giả trong `tests/conftest.py`.

```bash
uv run pytest tracks/devops/sample-app -q
```
