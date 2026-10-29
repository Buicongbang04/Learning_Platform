# M08: CI/CD và hạ tầng bằng Terraform

## Mục tiêu

Đưa dự án lên chuẩn làm việc nhóm: mọi push đều được lint và test tự động, hạ tầng (bucket,
user, policy MinIO; schema Postgres) được khai báo bằng code và dựng lại được.

## Việc cần làm

1. **Đóng gói**: viết `project/infra/Dockerfile` cho phần ingestion/streaming (base
   `python:3.12-slim`, cài bằng `uv`, user không phải root, multi-stage để image nhỏ).
   Build thử:

   ```bash
   docker build -f tracks/data-engineer/capstone/project/infra/Dockerfile -t olist-pipeline:dev tracks/data-engineer/capstone/project
   ```

2. **Terraform** trong `project/infra/terraform/`:
   - Provider `aminueza/minio`: tạo bucket `olist`, bật versioning, user `pipeline` với policy
     chỉ đọc/ghi prefix `bronze/`, `silver/`, `gold/`; user `bi_reader` chỉ đọc `gold/`.
   - Provider `cyrilgdn/postgresql`: tạo schema `raw`, `dw`, `stream`, role `analyst` chỉ `SELECT` trên `dw`.
   - Biến nhạy cảm qua `TF_VAR_*`, không commit `terraform.tfstate` (thêm vào `.gitignore` của dự án).

   ```bash
   docker compose -f setup/docker-compose.yml up -d postgres minio
   cd tracks/data-engineer/capstone/project/infra/terraform
   terraform init && terraform plan && terraform apply
   ```

3. **CI** – `.github/workflows/ci.yml` (đặt ở repo portfolio của bạn, bản nháp lưu tại
   `project/infra/ci.yml`):
   - Job `lint`: `ruff check`, `sqlfluff lint` cho SQL/dbt.
   - Job `test`: `uv sync`, `uv run pytest` (test không cần Docker).
   - Job `integration` (tuỳ chọn): service container `postgres:16`, chạy M01 ingest + `dbt build`.
   - Job `terraform`: `terraform fmt -check` và `terraform validate`.
4. **CD** (tuỳ chọn): build và push image lên GitHub Container Registry khi tag `v*`.
5. **Monitoring tối thiểu**: DAG Airflow gửi log/callback khi fail; ghi số dòng mỗi lần chạy vào
   bảng `ops.pipeline_runs` để theo dõi xu hướng.
6. Tạo `project/Makefile` (hoặc `justfile`) với các lệnh: `make up`, `make data`, `make ingest`,
   `make dbt`, `make test`, `make down`. `make data` tải bộ thật (`uv run python data/download_olist.py`,
   `uv run python data/download_dataset.py nyc-tlc`), bỏ qua tệp đã có; thiếu Kaggle token thì báo rõ và gợi ý
   `uv run python data/generate_olist.py --out data/raw/olist_synthetic`. CI dùng bộ giả lập nhỏ, không tải dữ liệu thật.

## Kết quả nộp

- `project/infra/Dockerfile`, `project/infra/terraform/*.tf`, `project/infra/ci.yml`, `project/Makefile`
- Badge CI trong README repo portfolio; ảnh một lần CI pass.

## Tiêu chí đạt

- [ ] `terraform apply` từ trạng thái trống tạo đủ bucket, user, policy, schema, role; chạy lại `plan` báo "No changes".
- [ ] User `bi_reader` không ghi được vào bucket (thử bằng `boto3`, nhận AccessDenied).
- [ ] CI chạy trên mỗi push và fail khi một test fail.
- [ ] Image Docker < 500 MB, chạy bằng user không phải root.
- [ ] Không có secret nào trong repo (kiểm bằng `git grep -i minioadmin` chỉ ra tệp ví dụ/README).
- [ ] `make up && make data && make ingest && make test` chạy được từ máy sạch.
