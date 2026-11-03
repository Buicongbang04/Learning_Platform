FROM python:3.12.11-slim AS build
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12.11-slim
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 app
WORKDIR /srv
COPY app ./app
USER app
EXPOSE 8000
CMD ["python", "-m", "app.serve"]
