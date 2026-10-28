---
title: DAG ELT Olist - nạp song song, dbt build, kiểm tra chất lượng và cảnh báo
level: advanced
services: []
files:
  - path: starter/dag_olist_elt.py
    note: 4 TODO
  - path: tests/test_dag_structure.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/05-batch-pipelines/exercises/advanced/02-airflow-dbt-orchestration -q
  - EXTRA_DAGS_DIR=$PWD/tracks/data-engineer/modules/05-batch-pipelines/exercises/advanced/02-airflow-dbt-orchestration/starter docker compose -f setup/airflow/docker-compose.yml up -d
---

## Mục tiêu

Thiết kế một DAG gần với production: sinh task động theo danh sách bảng, nhóm bằng `TaskGroup`,
gọi dbt, chặn publish bằng kiểm tra chất lượng, cảnh báo khi lỗi, và cấu hình để backfill an toàn.
Đây cũng là khung cho milestone m05 của capstone.

## Đề bài

Viết `starter/dag_olist_elt.py` (Airflow 2.x) tạo DAG `olist_elt`:

- Lịch `schedule="0 3 * * *"`, `start_date=datetime(2018, 1, 1)`, `catchup=True` (muốn backfill
  lịch sử khi bật lần đầu) nhưng giới hạn `max_active_runs` trong khoảng 1–3.
- `default_args`: `retries >= 2`, `retry_delay`, `execution_timeout` (đều là `timedelta`),
  `on_failure_callback=notify_failure`. `notify_failure(context)` ghi log/cảnh báo, không được raise.
- `TaskGroup("ingest")`: với mỗi bảng trong `TABLES` (`orders, customers, order_items, payments`)
  sinh hai task `wait_<bảng>` (`FileSensor`, `mode="reschedule"`, `filepath` có template `{{ ds }}`)
  và `load_<bảng>` (`PythonOperator` gọi `load_table` với `op_kwargs={"table": <bảng>}`),
  `wait_x >> load_x`. Các bảng nạp **song song**, không phụ thuộc nhau.
- `dbt_build` (`BashOperator`, lệnh có `dbt build` và `{{ ds }}`) chạy sau **mọi** `load_*`.
- `quality_check` (`PythonOperator`) sau `dbt_build`, rồi `publish` sau `quality_check`.
- `alert_on_failure` với `trigger_rule="one_failed"`, đứng sau cả `dbt_build` và `quality_check`.
- Top-level của tệp không làm I/O (không `connect`, `read_csv`, `open`, request HTTP, `now()`).
  Import thư viện nặng (duckdb, pandas) bên trong hàm.

Nội dung `load_table` và `quality_check` do bạn quyết định (gợi ý: DuckDB, delete-insert theo
`ds`); test chỉ kiểm cấu trúc DAG bằng bản giả lập API Airflow. Để chạy thật, bật Airflow bằng
lệnh thứ hai ở trên và thử backfill:
`airflow dags backfill -s 2018-01-01 -e 2018-01-03 olist_elt`.

## Tiêu chí đạt

- Cấu hình DAG phục vụ backfill: `catchup=True`, `max_active_runs <= 3`, retry, timeout, callback.
- Đủ 8 task trong group `ingest` với id `ingest.wait_<bảng>`, `ingest.load_<bảng>`, nạp song song.
- `dbt_build` chờ mọi `load_*`; chuỗi `dbt_build >> quality_check >> publish`.
- `alert_on_failure` chỉ chạy khi một task phía trước lỗi.
- Không có I/O ở top-level.
- Tự đánh giá thêm theo rubric trong lời giải.

## Gợi ý

### Gợi ý 1

```python
with TaskGroup("ingest") as ingest:
    for t in TABLES:
        wait = FileSensor(task_id=f"wait_{t}", filepath=LANDING + "/{{ ds }}/" + f"{t}.csv", mode="reschedule")
        load = PythonOperator(task_id=f"load_{t}", python_callable=load_table, op_kwargs={"table": t})
        wait >> load
ingest >> dbt_build
```

Chú ý: viết `{{ ds }}` trong f-string phải nhân đôi ngoặc (`{{{{ ds }}}}`), nên dễ hơn là nối chuỗi.

### Gợi ý 2

`[dbt_build, quality_check] >> alert_on_failure` với
`EmptyOperator(task_id="alert_on_failure", trigger_rule=TriggerRule.ONE_FAILED)`. Khi mọi thứ thành
công, task này ở trạng thái `skipped`/`upstream_failed` là bình thường.
