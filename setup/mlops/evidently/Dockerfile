FROM python:3.12.11-slim

RUN pip install --no-cache-dir --retries 10 --timeout 60 "evidently==0.7.23" "pandas==2.3.3" "pyarrow==21.0.0"

WORKDIR /work
ENV HOME=/tmp DO_NOT_TRACK=1
