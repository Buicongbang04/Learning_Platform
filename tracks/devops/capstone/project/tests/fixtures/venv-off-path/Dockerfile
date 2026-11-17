FROM python:3.12.16-slim-trixie AS deps
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install -r /tmp/requirements.txt

FROM python:3.12.16-slim-trixie AS runtime
COPY --from=deps /opt/venv /opt/venv
WORKDIR /srv
COPY olist_shop ./olist_shop
USER 10001:10001

FROM runtime AS worker
CMD ["/opt/venv/bin/python", "-m", "olist_shop.worker"]

FROM runtime AS api
CMD ["/opt/venv/bin/uvicorn", "olist_shop.main:app", "--host", "0.0.0.0", "--port", "8000"]
