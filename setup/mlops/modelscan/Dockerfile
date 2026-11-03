FROM python:3.12.11-slim@sha256:47ae396f09c1303b8653019811a8498470603d7ffefc29cb07c88f1f8cb3d19f

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --retries 10 --timeout 60 --require-hashes --no-deps -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

WORKDIR /work
ENV HOME=/tmp
