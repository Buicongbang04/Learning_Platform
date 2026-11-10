FROM python:3.12.11-slim

RUN pip install --no-cache-dir --retries 10 --timeout 60 mlflow==3.17.1 psycopg2-binary==2.9.10 boto3==1.40.61

EXPOSE 5000
