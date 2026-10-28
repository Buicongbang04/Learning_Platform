---
title: Multi-stage Dockerfile và Docker Compose cho job + PostgreSQL
level: intermediate
services: []
files:
  - path: starter/Dockerfile
    note: 4 TODO
  - path: starter/docker-compose.yml
    note: 4 TODO
  - path: tests/test_multistage_compose.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/intermediate/01-multistage-compose -q
---

## Mục tiêu

Tách stage build và runtime để image nhỏ và an toàn, và mô tả môi trường local gồm job + database
bằng Docker Compose với healthcheck, biến môi trường và volume đúng cách.

## Đề bài

Job `olist-loader` cần `psycopg` build từ source (cần `build-essential`, `libpq-dev`) nhưng lúc
chạy chỉ cần `libpq5`. Hoàn thiện:

**`starter/Dockerfile`** (multi-stage):

- Stage đầu đặt tên bằng `AS builder`, cài công cụ build và tạo wheel vào `/wheels`
  (`pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt`).
- Stage cuối (stage runtime) dùng base image đã pin version, **không** cài `build-essential`/`gcc`,
  lấy wheel bằng `COPY --from=builder`, cài bằng `pip install --no-cache-dir`.
- Mọi `FROM` pin phiên bản (không `latest`, không thiếu tag).
- Stage cuối có `USER` không phải root, có `HEALTHCHECK`, và `ENTRYPOINT`/`CMD` exec form chạy
  `python -m loader`.

**`starter/docker-compose.yml`**:

- Service `postgres` dùng image `postgres` pin phiên bản (vd. `postgres:16.4`), mật khẩu lấy từ
  biến `${POSTGRES_PASSWORD}` (không hardcode), dữ liệu lưu ở **named volume** khai báo trong
  `volumes:` cấp cao nhất, và có `healthcheck` dùng `pg_isready`.
- Service `loader` build từ `.`, `depends_on` postgres với `condition: service_healthy`, và kết nối
  DB bằng hostname `postgres` (không phải `localhost`) qua biến `DATABASE_URL`.

## Tiêu chí đạt

- Dockerfile có ít nhất 2 stage, stage đầu có `AS builder`, stage cuối có `COPY --from=builder`.
- Mọi `FROM` có tag phiên bản chứa số, không phải `latest`.
- Stage cuối không có `build-essential`/`gcc`, có `USER` khác root, `HEALTHCHECK`, exec form.
- Mọi `pip install`/`pip wheel` có `--no-cache-dir`.
- Compose: `postgres` image pin phiên bản, `POSTGRES_PASSWORD` dạng `${...}`, không có mật khẩu
  viết thẳng ở bất kỳ service nào.
- Compose: `postgres` có healthcheck chứa `pg_isready`, mount một named volume đã khai báo.
- Compose: `loader` có `build`, `depends_on.postgres.condition == service_healthy`, `DATABASE_URL`
  chứa `@postgres:5432`.

## Gợi ý

### Gợi ý 1

`depends_on: [postgres]` chỉ chờ container **khởi động**, không chờ Postgres **sẵn sàng nhận kết
nối**. Dạng mapping `depends_on: {postgres: {condition: service_healthy}}` mới chờ healthcheck.

### Gợi ý 2

Healthcheck trong compose: `test: ["CMD-SHELL", "pg_isready -U de -d olist"]`. Biến
`${POSTGRES_PASSWORD}` được Compose đọc từ tệp `.env` cạnh compose hoặc từ môi trường shell.
