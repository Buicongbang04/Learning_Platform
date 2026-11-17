FROM python:3.12.16-slim-trixie AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

FROM python:3.12.16-slim-trixie AS runtime
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN groupadd --system --gid 10001 olist \
 && useradd --system --uid 10001 --gid olist --no-create-home --shell /usr/sbin/nologin olist
COPY --from=build /opt/venv /opt/venv
WORKDIR /srv
COPY --chown=root:root olist_shop ./olist_shop
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["uvicorn", "olist_shop.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
