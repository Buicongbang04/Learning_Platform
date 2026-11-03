FROM python:3.12.11-slim
ENV PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 app
WORKDIR /srv
COPY lab.py .
USER 10001
EXPOSE 8080
CMD ["python", "/srv/lab.py"]
