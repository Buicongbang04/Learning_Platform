FROM python:3.12.11-slim

RUN pip install --no-cache-dir --retries 10 --timeout 60 "feast[redis]==0.67.0"

WORKDIR /repo
ENV HOME=/tmp FEAST_USAGE=False
