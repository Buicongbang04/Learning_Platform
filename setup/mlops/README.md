# Stack MLOps cục bộ

Một project Compose riêng (`mlops`), tách khỏi `setup/docker-compose.yml`, gồm:

| Service | Vai trò | Cổng trên máy (mặc định) |
| --- | --- | --- |
| `postgres` | backend store của MLflow (user/pass `mlops`/`mlops`, db `mlflow`) | `127.0.0.1:25433` |
| `minio` | artifact store S3 (`minioadmin`/`minioadmin`) | API `127.0.0.1:29000`, console `127.0.0.1:29001` |
| `minio-init` | chạy một lần, tạo bucket `mlflow` và `dvc` | không có |
| `mlflow` | MLflow 3.17.1 tracking server, `--serve-artifacts` | `127.0.0.1:25000` |

Các cổng mặc định nằm ở dải 2xxxx vì 5432, 9000, 5000, 8000 thường đã bị chiếm. Đổi cổng bằng biến
`MLOPS_PG_PORT`, `MLOPS_MINIO_PORT`, `MLOPS_MINIO_CONSOLE_PORT`, `MLOPS_MLFLOW_PORT` trong `setup/.env`
(xem `setup/.env.example`). Compose chỉ đọc `.env` cạnh tệp compose (`setup/mlops/`), nên khi đã đổi cổng trong `setup/.env`, mọi lệnh phải thêm `--env-file setup/.env` (xem bên dưới). Mọi cổng chỉ bind `127.0.0.1`.

## Bật

```bash
# từ gốc repo
nice -n 15 docker compose -f setup/mlops/compose.yaml up -d --build --wait
```

Đã đổi cổng trong `setup/.env`: thêm `--env-file setup/.env` trước `-f`, để stack và test (đọc `setup/.env`) dùng cùng cổng:

```bash
docker compose --env-file setup/.env -f setup/mlops/compose.yaml up -d --build --wait
```

Lần đầu build image MLflow mất vài phút (cài `mlflow`, `psycopg2-binary`, `boto3`). Nếu build đứt giữa
chừng vì mạng, chạy lại lệnh trên. Muốn giới hạn CPU như stack DevOps, đặt `DEVOPS_CPUSET` (vd. `12-35`).

## Kiểm

```bash
docker compose -f setup/mlops/compose.yaml ps -a       # postgres, minio, mlflow: healthy; minio-init: exited (0)
# Đã đổi cổng trong setup/.env thì dùng dòng này thay cho dòng trên:
docker compose --env-file setup/.env -f setup/mlops/compose.yaml ps -a
curl -s http://127.0.0.1:25000/health                  # OK
```

Mở http://127.0.0.1:25000 (MLflow UI) và http://127.0.0.1:29001 (console MinIO).

## Cấu hình cho client (máy host)

```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:25000
export MLFLOW_S3_ENDPOINT_URL=http://127.0.0.1:29000
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
export MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false   # bắt buộc khi tải model/artifact từ host
```

Vì server chạy với `--serve-artifacts`, client đẩy artifact qua HTTP tới MLflow (proxy), nên thường chỉ
cần `MLFLOW_TRACKING_URI`. `MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false` là bắt buộc để `mlflow.pyfunc.load_model("models:/...")` hoặc `download_artifacts` chạy trên host: MLflow 3.17 server tự quảng bá tải multipart qua presigned URL trỏ `minio:9000` (tên chỉ phân giải trong mạng Compose), client mặc định sẽ treo; server không có cờ tắt tính năng này. Hai biến `AWS_*` và `MLFLOW_S3_ENDPOINT_URL` cần khi client đọc/ghi thẳng
MinIO (ví dụ `boto3`, DVC remote `s3://dvc`).

Gọi MLflow từ container khác: nối vào network `mlops_default` và dùng `http://mlflow:5000` (server đã cho phép Host `mlflow`, `localhost`, `127.0.0.1` qua `--allowed-hosts`; Host khác bị 403).

## Tắt và xoá dữ liệu

```bash
docker compose -f setup/mlops/compose.yaml down        # giữ dữ liệu (volume mlops_pg, mlops_minio)
docker compose -f setup/mlops/compose.yaml down -v     # xoá cả run, model và artifact
# Đã đổi cổng trong setup/.env thì thêm --env-file, ví dụ:
docker compose --env-file setup/.env -f setup/mlops/compose.yaml down
```

## Lỗi hay gặp

- `port is already allocated`: cổng đã bị chiếm, đổi biến `MLOPS_*_PORT` trong `setup/.env` rồi chạy lại với `--env-file setup/.env` (không có cờ này, Compose bỏ qua `setup/.env`).
- `mlflow` chưa healthy: xem `docker compose -f setup/mlops/compose.yaml logs mlflow`; thường do `postgres` hoặc `minio-init` chưa xong.
- Artifact không lên MinIO: kiểm bucket `mlflow` đã có (`minio-init` exited 0).
