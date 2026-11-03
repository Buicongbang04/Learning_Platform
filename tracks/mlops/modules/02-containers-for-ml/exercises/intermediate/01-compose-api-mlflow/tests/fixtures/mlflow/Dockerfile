FROM python:3.12.11-slim
RUN pip install --no-cache-dir --retries 10 --timeout 60 \
    mlflow-skinny==3.17.1 Flask==3.1.3 gunicorn==26.2.0 SQLAlchemy==2.1.6 alembic==1.20.1 \
    flask-cors==6.0.5 pandas==3.1.0 aiohttp==3.14.5
RUN useradd --system --uid 10001 --create-home mlflow && mkdir /mlflow-data && chown mlflow /mlflow-data
USER mlflow
WORKDIR /home/mlflow
EXPOSE 5000
