# Airflow cho lộ trình Data Engineer

Airflow 2.10.5, `LocalExecutor`, metadata DB là một Postgres riêng (`airflow-db`, không publish cổng),
tách khỏi Postgres `de` dùng cho bài tập.

## Chạy

```bash
# từ gốc repo
docker compose -f setup/airflow/docker-compose.yml up -d
docker compose -f setup/airflow/docker-compose.yml ps        # chờ webserver "healthy"
```

Mở http://localhost:8080, đăng nhập `airflow` / `airflow`. Lần đầu mất 1–3 phút vì container
chạy `airflow db migrate` và cài thư viện trong `_PIP_ADDITIONAL_REQUIREMENTS`.

Tắt: `docker compose -f setup/airflow/docker-compose.yml down` (thêm `-v` để xoá metadata và log).

## Thư mục được mount

| Trên máy | Trong container | Dùng cho |
| --- | --- | --- |
| `tracks/data-engineer/capstone/project/dags` | `/opt/airflow/dags` | DAG của capstone |
| `$EXTRA_DAGS_DIR` (mặc định `setup/airflow/extra_dags`) | `/opt/airflow/dags/extra` | DAG của module 05 hoặc thử nghiệm |
| `tracks/data-engineer/capstone/project` | `/opt/airflow/project` | dbt project, script ingestion |
| `data/` | `/opt/airflow/data` | CSV Olist (`/opt/airflow/data/raw`) |

Chạy kèm DAG của module 05:

```bash
EXTRA_DAGS_DIR=$PWD/tracks/data-engineer/modules/05-batch-pipelines \
  docker compose -f setup/airflow/docker-compose.yml up -d
```

## Kết nối tới dịch vụ dùng chung

Airflow chạy ở project Compose riêng, nên DAG gọi các dịch vụ trong `setup/docker-compose.yml`
qua `host.docker.internal` (cổng đã publish ra máy host):

- Connection có sẵn `olist_postgres` → `postgresql://de:de@host.docker.internal:5432/de`
- Biến môi trường `MINIO_ENDPOINT=http://host.docker.internal:9000`, `KAFKA_BOOTSTRAP=host.docker.internal:9094`

## Sự cố thường gặp

- **Lỗi quyền ghi log / DAG**: đặt `AIRFLOW_UID=$(id -u)` trước lệnh `up`
  (`echo "AIRFLOW_UID=$(id -u)" > setup/airflow/.env`).
- **DAG không hiện**: lỗi import xem ở banner đỏ trên UI hoặc
  `docker compose -f setup/airflow/docker-compose.yml exec airflow-scheduler airflow dags list-import-errors`.
- **Cổng 8080 trùng**: đổi `"8080:8080"` thành `"8081:8080"`.
- **Khởi động chậm vì pip**: đặt `AIRFLOW_EXTRA_PIP=""` nếu DAG không cần dbt/duckdb.
