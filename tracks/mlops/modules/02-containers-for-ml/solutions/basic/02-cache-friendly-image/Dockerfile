FROM python:3.12.11-slim AS deps
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12.11-slim
ENV PATH=/opt/venv/bin:$PATH MODEL_PATH=/models/model.joblib PYTHONUNBUFFERED=1
COPY --from=deps /opt/venv /opt/venv
WORKDIR /srv
COPY model.joblib /models/model.joblib
COPY app ./app
CMD ["python", "-m", "app.serve"]
