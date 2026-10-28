---
title: Viết Dockerfile chuẩn cho job ingest Python
level: basic
services: []
files:
  - path: starter/Dockerfile
    note: 6 TODO
  - path: starter/.dockerignore
    note: 1 TODO
  - path: tests/test_dockerfile_python_job.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/basic/01-dockerfile-python-job -q
---

## Mục tiêu

Viết được một Dockerfile cho job Python theo các quy tắc mà reviewer hay đòi: pin base image, tận
dụng layer cache, không cache pip, không chạy root, exec form, và một `.dockerignore` hợp lý.

## Đề bài

Đội có job `src/ingest_orders.py` nạp đơn hàng Olist vào PostgreSQL. Dependency nằm ở
`requirements.txt`. Dockerfile trong `starter/` build được nhưng mắc nhiều lỗi. Sửa
`starter/Dockerfile` và `starter/.dockerignore` để đạt các tiêu chí dưới đây. Test chỉ đọc và phân
tích tệp, không cần bật Docker (nếu có Docker, bạn có thể tự thử `docker build`).

Job được chạy bằng `python -m src.ingest_orders`.

## Tiêu chí đạt

- Có đúng một `FROM`, image có tag cụ thể chứa số phiên bản (vd. `python:3.12-slim`), không phải
  `latest` hay không tag.
- Có `WORKDIR`.
- `COPY requirements.txt` xuất hiện **trước** `RUN pip install`, và lệnh copy mã nguồn
  (`COPY src` hoặc `COPY .`) xuất hiện **sau** `RUN pip install`.
- Mọi lệnh `pip install` có `--no-cache-dir`.
- Có `USER` khác `root`/`0`, đặt sau các lệnh cài đặt.
- `CMD` hoặc `ENTRYPOINT` cuối cùng dùng exec form (mảng JSON) và chạy module `src.ingest_orders`.
- Không có `ENV`/`ARG` chứa `PASSWORD`, `SECRET` hay `TOKEN`.
- `.dockerignore` có `.git`, `__pycache__`, `.venv` và `data`.

## Gợi ý

### Gợi ý 1

Docker build lại mọi layer sau layer đầu tiên bị thay đổi. Tách `COPY requirements.txt .` +
`RUN pip install ...` ra trước, rồi mới copy code.

### Gợi ý 2

Tạo user bằng `RUN useradd --create-home --uid 10001 appuser` rồi `USER appuser`. Exec form trông
như `ENTRYPOINT ["python", "-m", "src.ingest_orders"]`. Mật khẩu DB truyền lúc `docker run -e`,
không đặt trong Dockerfile.
