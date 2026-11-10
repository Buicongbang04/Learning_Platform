FROM python:3.12.16-slim-trixie
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# TODO 1: sửa một dòng code là pip install chạy lại từ đầu; sắp lại thứ tự để layer cài dependency chỉ build lại khi requirements.txt đổi
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

USER 10001
CMD ["python", "export_orders.py"]
