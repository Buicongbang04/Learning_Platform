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
    # Thực tế: copy /data/landing/orders_<ds_nodash>.csv sang vùng raw, có thể kèm kiểm tra schema.
    return f"/data/raw/orders/{ds}.csv"


def transform_orders(ti, ds, **context):
    """Lấy đường dẫn thô từ XCom của extract_orders, trả về đường dẫn parquet sạch."""
    raw_path = ti.xcom_pull(task_ids="extract_orders")
    clean_path = raw_path.replace("/raw/", "/clean/").replace(".csv", ".parquet")
    # Thực tế: đọc raw_path, làm sạch, ghi clean_path.
    return clean_path


def load_orders(ti, ds, **context):
    """Lấy đường dẫn parquet từ XCom của transform_orders, trả về thông báo đã nạp."""
    clean_path = ti.xcom_pull(task_ids="transform_orders")
    # Thực tế: delete-insert partition ds vào warehouse.
    return f"loaded {clean_path} into fct_orders (ds={ds})"


default_args = {
    "owner": "data-eng",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}

with DAG(
    dag_id="olist_daily",
    schedule="@daily",
    start_date=datetime(2018, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["olist"],
    default_args=default_args,
) as dag:
    wait_orders_file = FileSensor(
        task_id="wait_orders_file",
        filepath="/data/landing/orders_{{ ds_nodash }}.csv",
        poke_interval=60,
        timeout=60 * 60,
        mode="reschedule",
    )
    extract = PythonOperator(task_id="extract_orders", python_callable=extract_orders)
    transform = PythonOperator(task_id="transform_orders", python_callable=transform_orders)
    load = PythonOperator(task_id="load_orders", python_callable=load_orders)
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd /opt/airflow/project/dbt && dbt build --select tag:daily --vars '{ds: {{ ds }}}'",
    )

    wait_orders_file >> extract >> transform >> load >> dbt_build
