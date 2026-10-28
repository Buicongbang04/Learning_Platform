# TODO 1: biến thành multi-stage: stage builder (AS builder) tạo wheel, stage runtime chỉ cài wheel
FROM python:3.12
RUN apt-get update && apt-get install -y build-essential libpq-dev
WORKDIR /app
COPY requirements.txt .
# TODO 2: dùng --no-cache-dir
RUN pip install -r requirements.txt
COPY loader/ ./loader/
# TODO 3: chạy bằng user không phải root, thêm HEALTHCHECK
# TODO 4: exec form
CMD python -m loader
