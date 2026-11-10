FROM python:3.12.16-slim-trixie
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY export_orders.py .

USER 10001
CMD ["python", "export_orders.py"]
