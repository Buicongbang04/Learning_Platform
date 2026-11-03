FROM python:3.12.11-slim

WORKDIR /srv
COPY . .
RUN pip install -r requirements.txt
ENV MODEL_PATH=/models/model.joblib PYTHONUNBUFFERED=1
RUN mkdir -p /models && mv model.joblib /models/model.joblib
EXPOSE 8000
CMD ["python", "-m", "app.serve"]
