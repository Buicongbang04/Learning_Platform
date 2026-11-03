FROM python:3.12.11-slim AS build
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12.11-slim
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH MODEL_PATH=/models/model.joblib PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 app
WORKDIR /srv
COPY app ./app
COPY model.joblib /models/model.joblib
USER app
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=5 CMD ["python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
CMD ["python", "-m", "app.serve"]
