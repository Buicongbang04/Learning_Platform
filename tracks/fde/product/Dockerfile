FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e

ARG QUILLO_VERSION=1.1.0
ENV QUILLO_VERSION=${QUILLO_VERSION} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock \
    && useradd --system --uid 10001 --user-group --home-dir /app --shell /usr/sbin/nologin quillo \
    && mkdir -p /data/inbox && chown 10001:10001 /data/inbox

COPY LICENSE ./
COPY migrations/ migrations/
COPY src/ src/

USER 10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"]
CMD ["uvicorn", "quillo.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
