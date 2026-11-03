FROM python:3.12.11-slim
RUN pip install --no-cache-dir --retries 10 --timeout 60 mlflow-skinny==3.17.1 flask gunicorn
RUN pip install --no-cache-dir --retries 10 --timeout 60 sqlalchemy alembic
RUN pip install --no-cache-dir --retries 10 --timeout 60 flask-cors pandas aiohttp
RUN useradd --system --uid 10001 --create-home mlflow && mkdir /mlflow-data && chown mlflow /mlflow-data
USER mlflow
WORKDIR /home/mlflow
EXPOSE 5000
