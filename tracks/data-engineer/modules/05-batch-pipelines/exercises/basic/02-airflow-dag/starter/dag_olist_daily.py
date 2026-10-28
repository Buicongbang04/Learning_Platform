"""DAG Airflow chạy pipeline đơn hàng Olist mỗi ngày.

Chuỗi task: wait_orders_file >> extract_orders >> transform_orders >> load_orders >> dbt_build
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.filesystem import FileSensor


def extract_orders(ds, **context):
    """Trả về đường dẫn file thô của ngày ds (giá trị trả về tự đẩy vào XCom)."""
    # TODO: trả về f"/data/raw/orders/{ds}.csv"
    raise NotImplementedError


def transform_orders(ti, ds, **context):
    """Lấy đường dẫn thô từ XCom của extract_orders, trả về đường dẫn parquet sạch."""
    # TODO: raw = ti.xcom_pull(task_ids="extract_orders"); trả về "/data/clean/orders/<ds>.parquet"
    raise NotImplementedError


def load_orders(ti, ds, **context):
    """Lấy đường dẫn parquet từ XCom của transform_orders, trả về thông báo đã nạp."""
    # TODO: trả về f"loaded {path} into fct_orders (ds={ds})"
    raise NotImplementedError


# TODO: default_args với retries >= 2 và retry_delay (timedelta >= 1 phút)
default_args = {
    "owner": "data-eng",
}

# TODO: dag_id="olist_daily", schedule="@daily", start_date=datetime(2018, 1, 1),
#       catchup=False, max_active_runs=1, tags=["olist"], default_args=default_args
with DAG(
    dag_id="TODO",
    start_date=datetime(2018, 1, 1),
    default_args=default_args,
) as dag:
    # TODO: FileSensor "wait_orders_file" chờ /data/landing/orders_{{ ds_nodash }}.csv, mode="reschedule"
    # TODO: 3 PythonOperator extract_orders / transform_orders / load_orders
    # TODO: BashOperator "dbt_build" chạy `dbt build` với --vars chứa {{ ds }}
    # TODO: nối phụ thuộc bằng >>
    pass
