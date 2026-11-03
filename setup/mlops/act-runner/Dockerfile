FROM python:3.12.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --retries 10 --timeout 60 uv==0.11.33

ENV UV_LINK_MODE=copy
