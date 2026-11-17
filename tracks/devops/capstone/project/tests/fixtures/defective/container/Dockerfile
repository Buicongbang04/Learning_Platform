FROM python:3.12.16-slim-trixie AS api
WORKDIR /srv
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD uvicorn olist_shop.main:app --host 0.0.0.0 --port 8000
