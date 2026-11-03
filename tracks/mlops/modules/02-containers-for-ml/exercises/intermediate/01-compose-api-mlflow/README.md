---
title: Compose hai dịch vụ - API dự đoán và MLflow có healthcheck
level: intermediate
services: []
files:
  - path: starter/compose.yaml
    note: Viết hai dịch vụ
  - path: starter/api.env
    note: Biến môi trường của API
  - path: tests/test_compose.py
    note: Không sửa
  - path: tests/fixtures/service/Dockerfile
    note: Image API (đọc, không sửa)
  - path: tests/fixtures/mlflow/Dockerfile
    note: Image MLflow server (đọc, không sửa)
run:
  - docker compose version
  - nice -n 15 uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/intermediate/01-compose-api-mlflow -q
---

## Mục tiêu

Dựng một stack nhiều dịch vụ bằng Compose đúng cách: thứ tự khởi động theo sức khoẻ thật, dữ liệu trên volume, cấu hình ngoài code, không chiếm cổng cố định của máy.

## Đề bài

Test dựng thư mục dự án tạm gồm `service/` (image API, **không** có model), `mlflow/` (image có `mlflow-skinny` 3.17.1 kèm Flask, gunicorn, SQLAlchemy, pandas, user thường, thư mục `/mlflow-data` ghi được), `models/model.joblib`, cùng `compose.yaml` và `api.env` của bạn. Lần build đầu mất vài phút vì cài MLflow (phụ thuộc tốc độ mạng); các lần sau dùng cache.

Viết `starter/compose.yaml` và `starter/api.env` với hai dịch vụ tên đúng `mlflow` và `api`:

- `mlflow`: build từ `./mlflow`, chạy `mlflow server --host 0.0.0.0 --port 5000` với **file store** (`--backend-store-uri` và `--default-artifact-root` là đường dẫn trong container). Dữ liệu ghi vào một **named volume** khai báo ở `volumes:` cấp cao nhất và mount vào container; hai đường dẫn trên phải nằm dưới điểm mount đó. MLflow 3.17 coi file store là chế độ bảo trì và từ chối chạy nếu thiếu biến môi trường `MLFLOW_ALLOW_FILE_STORE=true`: đặt nó cho dịch vụ. MLflow 3.x còn kiểm header `Host` để chống DNS rebinding: server phải cho phép host `mlflow:5000` mà API dùng (và `localhost`, `127.0.0.1` cho test), nếu không API nhận 403 (xem `mlflow server --help`, mục Security). Endpoint `/health` của MLflow dùng cho healthcheck.
- `api`: build từ `./service`, mount `./models` vào `/models` chỉ đọc. `MODEL_PATH` và `MLFLOW_TRACKING_URI` (địa chỉ MLflow trong network của Compose) nằm trong `api.env`, nạp bằng `env_file`. Service nghe cổng 8000 và có `/healthz`.
- Cả hai có `healthcheck` với `test`, `interval`, `retries` (image slim không có `curl`).
- `api` chỉ khởi động khi `mlflow` đã healthy: `depends_on` dạng map với `condition: service_healthy`.
- Cả hai dịch vụ publish cổng container của mình (`api` 8000, `mlflow` 5000) mà không bind cổng cố định trên host (test lấy cổng bằng `docker compose port`; cú pháp ngắn hay dài đều được): khai báo cổng container (vd. `"8000"`) hoặc `127.0.0.1::8000`, để Docker chọn cổng trống và nhiều dự án chạy song song được.

## Tiêu chí đạt

- `nice -n 15 uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/intermediate/01-compose-api-mlflow -q` pass: stack lên healthy (`up --wait`), `POST /predict` trả `run_id` và MLflow có metric `predictions` bằng số dòng đã gửi, dữ liệu MLflow nằm trên volume (thư mục mount không rỗng sau khi API ghi metric).
- Giải thích được vì sao `depends_on` không kèm `condition` chỉ đảm bảo thứ tự khởi động chứ không đảm bảo dịch vụ sẵn sàng, và vì sao file store không dùng được khi nhiều người cùng ghi.

## Gợi ý

### Gợi ý 1

`docker compose config` in ra cấu hình đã gộp, kiểm lỗi cú pháp trước khi build.

### Gợi ý 2

Khi stack không lên, `docker compose ps` cho biết dịch vụ nào unhealthy, `docker compose logs <dịch vụ>` cho biết vì sao.
