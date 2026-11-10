# Stack MLOps cục bộ

Một project Compose riêng (`mlops`), tách khỏi `setup/docker-compose.yml`, gồm:

| Service | Vai trò | Cổng trên máy (mặc định) |
| --- | --- | --- |
| `postgres` | backend store của MLflow (user/pass `mlops`/`mlops`, db `mlflow`) | `127.0.0.1:25433` |
| `minio` | artifact store S3 (`minioadmin`/`minioadmin`) | API `127.0.0.1:29000`, console `127.0.0.1:29001` |
| `minio-init` | chạy một lần, tạo bucket `mlflow` và `dvc` | không có |
| `mlflow` | MLflow 3.17.1 tracking server, `--serve-artifacts` | `127.0.0.1:25000` |

Các cổng mặc định nằm ở dải 2xxxx vì 5432, 9000, 5000, 8000 thường đã bị chiếm. Đổi cổng bằng biến
`MLOPS_PG_PORT`, `MLOPS_MINIO_PORT`, `MLOPS_MINIO_CONSOLE_PORT`, `MLOPS_MLFLOW_PORT` (và `MLOPS_PROMETHEUS_PORT`, `MLOPS_ALERTMANAGER_PORT`, `MLOPS_GRAFANA_PORT`, `MLOPS_REDIS_PORT`, `MLOPS_KAFKA_PORT` cho các profile bên dưới) trong `setup/.env`
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

## Bật thêm profile (Giai đoạn 2)

Hai profile tuỳ chọn, mặc định không chạy cùng stack lõi:

| Profile | Service | Cổng trên máy (mặc định) | Biến `.env` |
| --- | --- | --- | --- |
| `monitoring` | `prometheus` (v3.5.0) | `127.0.0.1:29090` | `MLOPS_PROMETHEUS_PORT` |
| `monitoring` | `alertmanager` (v0.34.1) | `127.0.0.1:29093` | `MLOPS_ALERTMANAGER_PORT` |
| `monitoring` | `grafana` (12.1.0, datasource Prometheus có sẵn, `admin`/`admin`) | `127.0.0.1:23000` | `MLOPS_GRAFANA_PORT` |
| `feast` | `redis` (7.4.5, online store của Feast) | `127.0.0.1:26390` | `MLOPS_REDIS_PORT` |

```bash
docker compose -f setup/mlops/compose.yaml --profile monitoring --profile feast up -d --wait
```

Feast không cài trong môi trường Python mặc định (nó kéo `pandas` xuống 2.3.3); mọi lệnh Feast chạy trong image
`mlops-feast:0.67.0` (build từ `setup/mlops/feast/Dockerfile`) qua `mlopskit.feast_run`. Image runner cho `act`
(`mlops-act-runner:1`, build từ `setup/mlops/act-runner/Dockerfile`) cũng do `mlopskit` build tại chỗ. Mỗi image này
mang nhãn `mlops-dockerfile-sha=<sha256 của Dockerfile>`; sửa Dockerfile thì lần gọi sau tự build lại cùng tag, không cần
`docker rmi`.

## Profile `streaming` (Giai đoạn 4)

| Profile | Service | Cổng trên máy (mặc định) | Biến `.env` |
| --- | --- | --- | --- |
| `streaming` | `kafka` (`apache/kafka:4.3.1`, ghim digest; KRaft 1 node, không ZooKeeper) | `127.0.0.1:29092` | `MLOPS_KAFKA_PORT` |

```bash
docker compose -f setup/mlops/compose.yaml --profile streaming up -d --wait
```

- Client trên máy dùng bootstrap `127.0.0.1:29092` (listener `HOST`); container trong mạng `mlops_default` dùng
  `kafka:9092` (listener `PLAINTEXT`). Đổi `MLOPS_KAFKA_PORT` thì địa chỉ quảng bá đổi theo (cần `--env-file setup/.env`).
- `auto.create.topics.enable=false`: topic phải tạo trước (test dùng `mlopskit.kafka_topic()`, tên `mlops-ex-<uuid8>`,
  xoá khi xong). `kafka_topic()` tạo **1 partition** trừ khi truyền `partitions=`; 3 partition chỉ là mặc định của broker
  cho topic tạo bằng công cụ khác (vd. `kafka-topics.sh` không có `--partitions`). Replication 1. Không có volume: xoá
  container là mất topic.
- Heap 256–512 MB, `mem_limit: 1g`; rảnh dùng ~320 MiB. Image ~690 MB trên đĩa (đo 2026-11-04).
- Client Python là `kafka-python-ng` 2.2.3 đã có trong môi trường mặc định (dùng ở DE module 07); đã kiểm
  produce/consume theo group, tạo/xoá topic với broker 4.3.1.

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
