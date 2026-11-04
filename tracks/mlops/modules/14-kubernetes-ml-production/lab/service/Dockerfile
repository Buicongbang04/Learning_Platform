FROM python:3.12.11-slim@sha256:47ae396f09c1303b8653019811a8498470603d7ffefc29cb07c88f1f8cb3d19f
ENV PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 app
WORKDIR /srv
COPY lab.py .
USER 10001
EXPOSE 8080
CMD ["python", "/srv/lab.py"]
