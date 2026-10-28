# Lời giải: DAG Airflow hằng ngày

## Cách làm

- `with DAG(...) as dag:` đặt DAG làm ngữ cảnh; mọi operator tạo trong khối đó tự gắn vào DAG.
- `catchup=False` để khi bật DAG lần đầu scheduler không tạo hàng trăm run từ 2018. Muốn chạy bù
  thì backfill có chủ đích: `airflow dags backfill -s 2018-01-01 -e 2018-01-31 olist_daily`.
- `max_active_runs=1` để các run không chồng lên nhau (an toàn khi load có thứ tự).
- `retries` + `retry_delay` + `retry_exponential_backoff` đặt trong `default_args` để mọi task
  thừa hưởng; task nào cần khác thì ghi đè trực tiếp.
- `FileSensor(mode="reschedule")`: giữa các lần kiểm tra, task nhả worker slot (trạng thái
  `up_for_reschedule`). Với `mode="poke"` mặc định, sensor chờ lâu sẽ chiếm hết worker.
- Hàm Python nhận `ds`, `ti` qua tham số: Airflow 2 truyền các biến context khớp tên tham số.
- XCom chỉ chứa **đường dẫn** (metadata nhỏ), dữ liệu thật nằm trong file/bảng.
- `bash_command` là trường template, nên `{{ ds }}` được render thành `2018-01-05` lúc chạy.

## Lỗi hay gặp

- `start_date=datetime.now()` hoặc `days_ago(1)`: lịch thay đổi mỗi lần scheduler parse file,
  run có thể không bao giờ được tạo.
- Nhầm `ds` là ngày chạy: run có `ds=2018-01-05` chạy lúc 2018-01-06 00:00 (cuối data interval).
- Đọc database hay file lớn ở top-level của tệp DAG: scheduler parse tệp này liên tục.
- Truyền DataFrame qua XCom: XCom lưu trong metadata DB, chỉ nên chứa vài KB.

## Kiểm tra trên Airflow thật

```bash
EXTRA_DAGS_DIR=$PWD/tracks/data-engineer/modules/05-batch-pipelines/solutions \
  docker compose -f setup/airflow/docker-compose.yml up -d
docker compose -f setup/airflow/docker-compose.yml exec airflow-scheduler \
  airflow dags list-import-errors
```

(Tên service có thể khác, xem `setup/airflow/docker-compose.yml`.)
