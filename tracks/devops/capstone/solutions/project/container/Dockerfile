FROM python:3.12.16-slim-trixie AS deps
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install -r /tmp/requirements.txt

FROM python:3.12.16-slim-trixie AS runtime
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN groupadd --system --gid 10001 olist \
 && useradd --system --uid 10001 --gid olist --no-create-home --shell /usr/sbin/nologin olist
COPY --from=deps /opt/venv /opt/venv
WORKDIR /srv
COPY olist_shop ./olist_shop
ARG APP_VERSION=dev
ARG GIT_COMMIT=unknown
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.title="olist-shop" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_COMMIT}"
USER 10001:10001

FROM runtime AS worker
ENV WORKER_METRICS_PORT=9101
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --start-interval=2s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9101/metrics', timeout=2)"]
CMD ["python", "-m", "olist_shop.worker"]

FROM runtime AS api
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --start-interval=2s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["uvicorn", "olist_shop.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
