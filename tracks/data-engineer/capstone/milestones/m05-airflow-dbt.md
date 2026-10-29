# M05: Orchestrate bằng Airflow + dbt

## Mục tiêu

Biến các script rời rạc ở M01–M04 thành một pipeline hằng ngày có lịch, retry, phụ thuộc rõ ràng,
backfill được. Chuyển phần transform `raw → dw` sang dbt để có test, docs và lineage.

## Việc cần làm

1. Tạo dự án dbt trong `project/models/olist_dbt/` (adapter `dbt-postgres` khi chạy trong Airflow,
   hoặc `dbt-duckdb` khi chạy local trên lakehouse). Cấu trúc:
   - `models/staging/stg_*.sql` (1:1 với bảng `raw`, đổi tên cột, ép kiểu)
   - `models/marts/fct_order_items.sql`, `dim_customer.sql`, `dim_product.sql`, `dim_seller.sql`
   - `snapshots/seller_snapshot.sql` (SCD2 bằng dbt snapshot, thay thế SQL tay ở M02)
   - `models/schema.yml` với test `unique`, `not_null`, `relationships`, `accepted_values`
     cho `order_status`.
2. Chạy dbt local:

   ```bash
   cd tracks/data-engineer/capstone/project/models/olist_dbt
   uv run dbt debug && uv run dbt build && uv run dbt docs generate
   ```

3. Viết DAG `project/dags/olist_daily.py` (`schedule="@daily"`, `catchup=False`,
   `max_active_runs=1`, `retries=2`, `retry_delay=5 phút`):

   ```mermaid
   flowchart LR
       A[kiểm tra CSV Olist] --> B[load_postgres]
       B --> C[dbt build]
       B --> D[to_bronze]
       D --> E[to_silver]
       E --> F[build_gold]
       C --> G[quality_gate]
       F --> G
   ```

   - Dùng `{{ ds }}` / `data_interval_start` làm tham số để mỗi lần chạy xử lý đúng ngày → idempotent.
   - Task dbt dùng `BashOperator` (hoặc Cosmos nếu muốn nâng cao).
   - Kết nối Postgres/MinIO qua Airflow Connections hoặc biến môi trường, không hard-code.
     `setup/airflow/docker-compose.yml` đã tạo sẵn connection `olist_postgres`
     (`host.docker.internal:5432`), biến `MINIO_ENDPOINT`, và mount `project/` vào
     `/opt/airflow/project`, `data/` vào `/opt/airflow/data` (CSV ở `/opt/airflow/data/raw`).
4. Bật Airflow và kích hoạt DAG:

   ```bash
   docker compose -f setup/docker-compose.yml up -d postgres minio
   docker compose -f setup/airflow/docker-compose.yml up -d
   # http://localhost:8080 (airflow / airflow) → bật DAG olist_daily → Trigger
   ```

5. Thử backfill 3 ngày và chạy lại một ngày đã chạy; xác nhận số dòng không đổi.
6. Viết test DAG `project/tests/test_dags.py`: import DAG không lỗi, không có cycle, đúng số task
   (bỏ qua nếu môi trường chưa có `airflow`: `pytest.importorskip("airflow")`).

## Kết quả nộp

- `project/models/olist_dbt/` (dbt project hoàn chỉnh)
- `project/dags/olist_daily.py`, `project/tests/test_dags.py`
- Ảnh chụp Graph view và một lần chạy thành công; ảnh lineage từ `dbt docs`.

## Tiêu chí đạt

- [ ] `dbt build` pass toàn bộ model, snapshot và test.
- [ ] DAG chạy thành công end-to-end trên Airflow.
- [ ] Chạy lại cùng một `logical_date` cho kết quả giống hệt (idempotent).
- [ ] Task lỗi tự retry; lỗi dữ liệu ở `quality_gate` làm DAG fail rõ ràng.
- [ ] Không có mật khẩu trong code DAG.
- [ ] README giải thích vì sao chọn ELT (transform trong warehouse) cho phần `raw → dw`.
