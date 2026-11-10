FROM python:3.12.11-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --system --uid 10001 app
WORKDIR /srv
COPY app.py model.joblib ./
ENV PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
