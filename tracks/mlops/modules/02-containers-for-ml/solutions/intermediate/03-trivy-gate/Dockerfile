FROM python:3.12.11-slim
RUN useradd --system --uid 10001 app
WORKDIR /srv
COPY app /srv/app
RUN pip install --no-cache-dir flask==3.1.2
USER app
HEALTHCHECK --interval=10s --timeout=3s CMD ["python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
CMD ["python", "-m", "app"]
