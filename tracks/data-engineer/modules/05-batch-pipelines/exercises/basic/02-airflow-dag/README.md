---
title: Viết DAG Airflow hằng ngày cho đơn hàng Olist
level: basic
services: []
files:
  - path: starter/dag_olist_daily.py
    note: 7 TODO
  - path: tests/test_dag.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/05-batch-pipelines/exercises/basic/02-airflow-dag -q
  - EXTRA_DAGS_DIR=$PWD/tracks/data-engineer/modules/05-batch-pipelines/exercises docker compose -f setup/airflow/docker-compose.yml up -d
---

## Mục tiêu

Viết một DAG Airflow 2.x đúng chuẩn: lịch chạy, `catchup`, retry, sensor, PythonOperator dùng
`ds` và XCom, BashOperator gọi dbt có Jinja template, và nối phụ thuộc bằng `>>`.

## Đề bài

Sửa `starter/dag_olist_daily.py` để tạo đúng **một** DAG:

- `dag_id="olist_daily"`, `schedule="@daily"`, `start_date=datetime(2018, 1, 1)`,
  `catchup=False`, `max_active_runs=1`, `tags=["olist"]`.
- `default_args` có `retries >= 2` và `retry_delay` là `timedelta` từ 1 phút trở lên.
- 5 task, nối thành chuỗi
  `wait_orders_file >> extract_orders >> transform_orders >> load_orders >> dbt_build`:
  - `wait_orders_file`: `FileSensor` chờ `/data/landing/orders_{{ ds_nodash }}.csv`,
    `mode="reschedule"` (không giữ worker slot khi chờ).
  - `extract_orders`, `transform_orders`, `load_orders`: `PythonOperator` gọi 3 hàm cùng tên.
  - `dbt_build`: `BashOperator` có lệnh chứa `dbt build` và truyền ngày bằng `{{ ds }}`
    (vd. `--vars '{ds: {{ ds }}}'`).
- Ba hàm Python (Airflow tự truyền `ds`, `ti` từ context):
  - `extract_orders(ds)` trả về `"/data/raw/orders/<ds>.csv"`.
  - `transform_orders(ti, ds)` lấy kết quả của `extract_orders` qua
    `ti.xcom_pull(task_ids="extract_orders")` và trả về `"/data/clean/orders/<ds>.parquet"`.
  - `load_orders(ti, ds)` lấy đường dẫn từ XCom của `transform_orders` và trả về
    `"loaded <path> into fct_orders (ds=<ds>)"`.
- Không dùng `datetime.now()`, `today()`, `days_ago()` trong tệp DAG.

Airflow không cài trong venv; test nạp DAG bằng một bản giả lập API Airflow để kiểm tra cấu trúc.
Muốn xem DAG trong UI thật, bật Airflow bằng lệnh thứ hai ở trên (DAG nằm ở
`/opt/airflow/dags/extra`, đăng nhập `airflow`/`airflow` tại http://localhost:8080).

## Tiêu chí đạt

- DAG có đúng `dag_id`, lịch, `start_date`, `catchup=False`, `max_active_runs=1`, tag `olist`.
- Retry cấu hình trong `default_args`.
- Đủ 5 task đúng loại operator, sensor dùng template `{{ ds_nodash }}` và `mode="reschedule"`.
- Phụ thuộc là một chuỗi thẳng đúng thứ tự.
- Các hàm trả về đúng giá trị và đọc XCom từ task trước.
- Không có `now()`/`days_ago()`.

## Gợi ý

### Gợi ý 1

Giá trị `return` của `python_callable` được Airflow tự đẩy vào XCom với key `return_value`;
task sau lấy bằng `ti.xcom_pull(task_ids="extract_orders")`.

### Gợi ý 2

```python
extract = PythonOperator(task_id="extract_orders", python_callable=extract_orders)
wait_orders_file >> extract >> transform >> load >> dbt_build
```

Đổi đường dẫn: `raw_path.replace("/raw/", "/clean/").replace(".csv", ".parquet")`.
