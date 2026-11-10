FROM python:3.12.16-slim-trixie AS build
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12.16-slim-trixie
ARG APP_VERSION=dev
RUN useradd --system --uid 10001 --no-create-home olist
COPY --from=build /opt/venv /opt/venv
WORKDIR /srv
COPY olist_shop ./olist_shop
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 APP_VERSION=${APP_VERSION}
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["uvicorn", "olist_shop.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
