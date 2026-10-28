FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependency trước: layer này chỉ build lại khi requirements.txt đổi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code sau: sửa code chỉ build lại từ đây
COPY src/ ./src/

RUN useradd --create-home --uid 10001 appuser
USER appuser

# Exec form: SIGTERM tới thẳng process Python
ENTRYPOINT ["python", "-m", "src.ingest_orders"]
