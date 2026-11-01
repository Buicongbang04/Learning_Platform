# TODO 1: tách thành ít nhất 2 stage: stage build cài dependency vào một venv, stage runtime chỉ chép venv và mã nguồn
FROM python:3.12.16-slim-trixie

# TODO 2: stage runtime không được còn gcc, make, libpq-dev; kiểm lại xem app có thật sự cần chúng không
RUN apt-get update && apt-get install -y build-essential libpq-dev curl

WORKDIR /srv
COPY . .
RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# TODO 3: tạo user không phải root (UID cố định) và chuyển sang user đó bằng USER

# TODO 4: HEALTHCHECK gọi /healthz bằng công cụ có sẵn trong image runtime (image slim không có curl nếu bạn không cài)

# TODO 5: CMD dạng exec (mảng JSON) để uvicorn là PID 1 và nhận SIGTERM
CMD uvicorn olist_shop.main:app --host 0.0.0.0 --port 8000 --no-access-log
