# Olist Data Platform

> README này là bản nháp cho repo portfolio của bạn. Viết lại dần sau mỗi milestone.

Nền tảng dữ liệu cho sàn thương mại điện tử Olist: ingest → warehouse → lakehouse →
orchestration → streaming → dashboard → governance.

## Quick start

```bash
uv sync
uv run python data/generate_olist.py --orders 50000
docker compose -f setup/docker-compose.yml up -d postgres
uv run python tracks/data-engineer/capstone/project/ingestion/load_postgres.py --data-dir data/raw
uv run pytest tracks/data-engineer/capstone/project/tests -q
```

## Cấu trúc

| Thư mục | Milestone | Nội dung |
| --- | --- | --- |
| `ingestion/` | M01, M03, M04, M06 | script nạp dữ liệu, job lakehouse, job Spark |
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
