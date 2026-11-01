FROM python:3.12.16-slim-trixie
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY worker.py entrypoint.sh ./
RUN chmod 0755 /app/entrypoint.sh
USER 10001
ENTRYPOINT ["/app/entrypoint.sh"]
