"""DAG ELT Olist: nạp 4 bảng thô song song -> dbt build -> kiểm tra chất lượng -> publish.

Yêu cầu chi tiết ở README của bài. Chỉ dùng Airflow 2.x API:
  airflow.DAG, airflow.operators.{python,bash,empty}, airflow.sensors.filesystem,
  airflow.utils.task_group.TaskGroup, airflow.utils.trigger_rule.TriggerRule
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

TABLES = ["orders", "customers", "order_items", "payments"]


def notify_failure(context):
    """on_failure_callback: gửi cảnh báo (ở đây chỉ in/log). Không được raise."""
    # TODO
    raise NotImplementedError


def load_table(table, ds, **context):
    """Nạp file landing của `table` ngày `ds` vào schema raw (idempotent theo ds)."""
    # TODO
    raise NotImplementedError


def quality_check(ds, **context):
    """Kiểm tra sau dbt (số dòng > 0, không trùng khoá...). Raise nếu không đạt."""
    # TODO
    raise NotImplementedError


# TODO: định nghĩa DAG "olist_elt" và toàn bộ task theo README
