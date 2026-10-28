# dags/

Thư mục này được mount vào Airflow (`setup/airflow/docker-compose.yml`). Đặt DAG của M05
(`olist_daily.py`) tại đây. Bật Airflow:

```bash
docker compose -f setup/airflow/docker-compose.yml up -d
```

Mở http://localhost:8080 (airflow / airflow).
