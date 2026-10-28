# TODO 1: pin phiên bản base image (vd. python:3.12-slim), không dùng latest
FROM python:latest

# TODO 2: đặt WORKDIR /app
# TODO 3: xoá secret khỏi Dockerfile, truyền lúc chạy bằng biến môi trường
ENV DB_PASSWORD=de

# TODO 4: copy requirements.txt và cài thư viện TRƯỚC khi copy code, dùng --no-cache-dir
COPY . .
RUN pip install -r requirements.txt

# TODO 5: tạo user không phải root và chuyển sang user đó

# TODO 6: dùng exec form (mảng JSON) thay vì shell form
CMD python -m src.ingest_orders
