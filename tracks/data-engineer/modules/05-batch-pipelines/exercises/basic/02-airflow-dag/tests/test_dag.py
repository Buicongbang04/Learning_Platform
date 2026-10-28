"""Kiểm tra DAG mà không cần cài Airflow.

Airflow chạy trong Docker riêng (setup/airflow/docker-compose.yml), không có trong venv. Test này
nạp tệp DAG với một bản giả lập tối thiểu của API Airflow 2.x (DAG, operator, `>>`) để đọc ra cấu
trúc. Nếu venv có Airflow thật, test cuối cùng nạp thêm bằng DagBag.
"""

import ast
import importlib.util
import sys
import types
from datetime import datetime, timedelta
from functools import cache

import pytest

from testkit import Exercise

ex = Exercise(__file__)
DAG_FILE = "dag_olist_daily.py"


# ---------------------------------------------------------------- Airflow giả lập
class FakeDAG:
    stack: list = []

    def __init__(self, dag_id, **kwargs):
        self.dag_id = dag_id
        self.kwargs = kwargs
        self.default_args = kwargs.get("default_args") or {}
        self.tasks = {}

    def __enter__(self):
        FakeDAG.stack.append(self)
        return self

    def __exit__(self, *exc):
        FakeDAG.stack.pop()


class FakeOperator:
    def __init__(self, task_id, dag=None, **kwargs):
        self.dag = dag or (FakeDAG.stack[-1] if FakeDAG.stack else None)
        if self.dag is None:
            raise RuntimeError(f"Task {task_id} không nằm trong DAG nào")
        self.task_id = task_id
        self.kind = type(self).__name__
        self.args = {**self.dag.default_args, **kwargs}
        self.upstream, self.downstream = set(), set()
        self.dag.tasks[task_id] = self

    def _link(self, other):
        for o in other if isinstance(other, (list, tuple)) else [other]:
            self.downstream.add(o.task_id)
            o.upstream.add(self.task_id)

    def set_downstream(self, other):
        self._link(other)

    def set_upstream(self, other):
        for o in other if isinstance(other, (list, tuple)) else [other]:
            o._link(self)

    def __rshift__(self, other):
        self._link(other)
        return other

    def __lshift__(self, other):
        self.set_upstream(other)
        return other

    def __rrshift__(self, other):
        self.set_upstream(other)
        return self

    def __rlshift__(self, other):
        self._link(other)
        return self


def _fake_modules():
    def op(name):
        return type(name, (FakeOperator,), {})

    mods = {
        "airflow": {"DAG": FakeDAG},
        "airflow.models": {"DAG": FakeDAG, "BaseOperator": FakeOperator},
        "airflow.operators": {},
        "airflow.operators.python": {"PythonOperator": op("PythonOperator")},
        "airflow.operators.bash": {"BashOperator": op("BashOperator")},
        "airflow.operators.empty": {"EmptyOperator": op("EmptyOperator")},
        "airflow.sensors": {},
        "airflow.sensors.filesystem": {"FileSensor": op("FileSensor")},
    }
    out = {}
    for name, attrs in mods.items():
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        out[name] = m
    return out


@cache
def load_dag():
    path = ex.path(DAG_FILE)
    saved = {k: sys.modules.get(k) for k in _fake_modules()}
    sys.modules.update(_fake_modules())
    try:
        spec = importlib.util.spec_from_file_location("fake_dag_" + str(abs(hash(str(path)))), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    dags = [v for v in vars(module).values() if isinstance(v, FakeDAG)]
    assert len(dags) == 1, "Tệp DAG phải tạo đúng một DAG ở top-level (vd. `with DAG(...) as dag:`)"
    return module, dags[0]


# ---------------------------------------------------------------- test
def test_dag_settings():
    _, dag = load_dag()
    assert dag.dag_id == "olist_daily"
    assert dag.kwargs.get("schedule") == "@daily"
    assert dag.kwargs.get("start_date") == datetime(2018, 1, 1)
    assert dag.kwargs.get("catchup") is False
    assert dag.kwargs.get("max_active_runs") == 1
    assert "olist" in (dag.kwargs.get("tags") or [])


def test_default_args_retry():
    _, dag = load_dag()
    assert dag.default_args.get("retries", 0) >= 2
    delay = dag.default_args.get("retry_delay")
    assert isinstance(delay, timedelta) and delay >= timedelta(minutes=1)


def test_tasks_and_operators():
    _, dag = load_dag()
    expected = {
        "wait_orders_file": "FileSensor",
        "extract_orders": "PythonOperator",
        "transform_orders": "PythonOperator",
        "load_orders": "PythonOperator",
        "dbt_build": "BashOperator",
    }
    assert {k: t.kind for k, t in dag.tasks.items()} == expected
    sensor = dag.tasks["wait_orders_file"]
    assert "{{ ds_nodash }}" in sensor.args.get("filepath", "")
    assert sensor.args.get("mode") == "reschedule"
    assert "dbt build" in dag.tasks["dbt_build"].args.get("bash_command", "")
    assert "{{ ds }}" in dag.tasks["dbt_build"].args.get("bash_command", "")


def test_dependencies_are_a_chain():
    _, dag = load_dag()
    chain = ["wait_orders_file", "extract_orders", "transform_orders", "load_orders", "dbt_build"]
    for up, down in zip(chain, chain[1:]):
        assert dag.tasks[up].downstream == {down}, f"{up} phải chạy ngay trước {down}"
    assert dag.tasks["wait_orders_file"].upstream == set()


def test_callables_use_ds_and_xcom():
    module, dag = load_dag()

    class TI:
        def __init__(self, values):
            self.values = values

        def xcom_pull(self, task_ids):
            return self.values[task_ids]

    extract = dag.tasks["extract_orders"].args["python_callable"]
    transform = dag.tasks["transform_orders"].args["python_callable"]
    load = dag.tasks["load_orders"].args["python_callable"]
    raw = extract(ds="2018-01-05")
    assert raw == "/data/raw/orders/2018-01-05.csv"
    clean = transform(ti=TI({"extract_orders": raw}), ds="2018-01-05")
    assert clean == "/data/clean/orders/2018-01-05.parquet"
    msg = load(ti=TI({"transform_orders": clean}), ds="2018-01-05")
    assert msg == "loaded /data/clean/orders/2018-01-05.parquet into fct_orders (ds=2018-01-05)"


def test_no_now_in_dag_file():
    tree = ast.parse(ex.read(DAG_FILE))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in {"now", "today", "utcnow"}:
            pytest.fail("Không dùng now()/today() trong DAG: dùng ds hoặc start_date cố định")
        if isinstance(node, ast.Name) and node.id == "days_ago":
            pytest.fail("Không dùng days_ago(): start_date phải cố định")


def test_real_airflow_dagbag():
    pytest.importorskip("airflow")
    from airflow.models import DagBag

    bag = DagBag(dag_folder=str(ex.path(DAG_FILE)), include_examples=False)
    assert not bag.import_errors
    assert "olist_daily" in bag.dags
