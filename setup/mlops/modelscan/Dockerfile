FROM python:3.12.11-slim

RUN pip install --no-cache-dir --retries 10 --timeout 60 \
    "modelscan==0.8.8" "numpy==2.5.4" "rich==14.3.4" "tomlkit==0.13.3" "click==8.5.0"

WORKDIR /work
ENV HOME=/tmp
