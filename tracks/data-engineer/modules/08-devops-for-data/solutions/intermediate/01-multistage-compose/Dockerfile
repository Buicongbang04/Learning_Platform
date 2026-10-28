# ---- Stage 1: build wheel (có compiler) ----
FROM python:3.12-slim AS builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- Stage 2: runtime tối giản ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY loader/ ./loader/
RUN useradd --create-home --uid 10001 appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python", "-c", "import loader"]
ENTRYPOINT ["python", "-m", "loader"]
