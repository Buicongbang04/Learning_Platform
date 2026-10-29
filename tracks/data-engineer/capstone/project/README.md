# Olist Data Platform

> README này là bản nháp cho repo portfolio của bạn. Viết lại dần sau mỗi milestone.

Nền tảng dữ liệu trên dữ liệu thật từ hai nguồn: sàn thương mại điện tử Olist và NYC TLC Yellow Taxi 2019.
Ingest → warehouse → lakehouse → orchestration → Spark → streaming → dashboard → governance.

## Quick start

```bash
uv sync
uv run python data/download_olist.py            # Olist thật, cần Kaggle token (xem data/download_olist.py)
uv run python data/download_dataset.py nyc-tlc  # NYC TLC 2019, ~1,2 GB (M06)
docker compose -f setup/docker-compose.yml up -d postgres
uv run python tracks/data-engineer/capstone/project/ingestion/load_postgres.py --data-dir data/raw
uv run pytest tracks/data-engineer/capstone/project/tests -q
```

## Cấu trúc

| Thư mục | Milestone | Nội dung |
| --- | --- | --- |
| `notebooks/` | Bước 0 | khám phá Olist thật, `report.md` (insight có số) |
| `ingestion/` | M01, M03, M04, M06 | script nạp dữ liệu, job lakehouse, job Spark NYC TLC |
| `models/` | M02, M04, M05, M09 | DDL `raw`/`dw`, SQL gold, dự án dbt `olist_dbt`, `mart` |
| `dags/` | M05 | DAG Airflow (mount vào `setup/airflow`) |
| `streaming/` | M07 | consumer Kafka, DDL schema `stream` |
| `infra/` | M08 | Dockerfile, Terraform, CI |
| `dashboards/` | M09 | Streamlit, export Metabase, Reverse ETL |
| `governance/` | M10 | data quality, lineage, masking |
| `tests/` | tất cả | `uv run pytest tracks/data-engineer/capstone/project/tests -q` |

## Kiến trúc

_(Dán sơ đồ mermaid kiến trúc của bạn ở đây.)_

## Design decisions

_(Ghi các quyết định: grain fact, idempotency, partitioning, delivery semantics… và lý do.)_

## Kết quả

_(Ảnh dashboard, số liệu benchmark, link CI.)_
