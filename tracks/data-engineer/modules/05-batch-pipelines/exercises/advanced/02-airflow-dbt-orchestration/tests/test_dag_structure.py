"""Kiểm tra cấu trúc DAG bằng bản giả lập API Airflow 2.x (Airflow không có trong venv)."""

import ast
import importlib.util
import sys
import types
from datetime import datetime, timedelta
from functools import cache

import pytest

from testkit import Exercise, use_solution

if use_solution():
    pytest.skip("Bài advanced chỉ có SOLUTION.md (hướng làm + rubric), không có code mẫu", allow_module_level=True)

ex = Exercise(__file__)
DAG_FILE = "dag_olist_elt.py"
TABLES = ["orders", "customers", "order_items", "payments"]


# ---------------------------------------------------------------- Airflow giả lập
class FakeDAG:
    stack: list = []

    def __init__(self, dag_id, **kwargs):
        self.dag_id, self.kwargs = dag_id, kwargs
        self.default_args = kwargs.get("default_args") or {}
        self.tasks = {}

    def __enter__(self):
        FakeDAG.stack.append(self)
        return self

    def __exit__(self, *exc):
        FakeDAG.stack.pop()


def _as_tasks(x):
    if isinstance(x, (list, tuple)):
        out = []
        for i in x:
            out += _as_tasks(i)
        return out
    return [x]


class _Linkable:
    def _roots(self):
        return [self]

    def _leaves(self):
        return [self]

    def __rshift__(self, other):
        for a in self._leaves():
            for o in _as_tasks(other):
                for b in o._roots():
                    a.downstream.add(b.task_id)
                    b.upstream.add(a.task_id)
        return other

    def __lshift__(self, other):
        for o in _as_tasks(other):
            o >> self
        return other

    def __rrshift__(self, other):
        for o in _as_tasks(other):
            o >> self
        return self

    def __rlshift__(self, other):
        self >> other
        return self


class FakeTaskGroup(_Linkable):
    stack: list = []

    def __init__(self, group_id, **kwargs):
        self.group_id = group_id
        self.members = []

    def __enter__(self):
        FakeTaskGroup.stack.append(self)
        return self

    def __exit__(self, *exc):
        FakeTaskGroup.stack.pop()

    def _roots(self):
        ids = {t.task_id for t in self.members}
        return [t for t in self.members if not (t.upstream & ids)]

    def _leaves(self):
        ids = {t.task_id for t in self.members}
        return [t for t in self.members if not (t.downstream & ids)]


class FakeOperator(_Linkable):
    def __init__(self, task_id, dag=None, **kwargs):
        self.dag = dag or (FakeDAG.stack[-1] if FakeDAG.stack else None)
        if self.dag is None:
            raise RuntimeError(f"Task {task_id} không nằm trong DAG nào")
        prefix = ".".join(g.group_id for g in FakeTaskGroup.stack)
        self.task_id = f"{prefix}.{task_id}" if prefix else task_id
        self.kind = type(self).__name__
        self.args = {**self.dag.default_args, **kwargs}
        self.upstream, self.downstream = set(), set()
        self.dag.tasks[self.task_id] = self
        for g in FakeTaskGroup.stack:
            g.members.append(self)

    def set_downstream(self, other):
        self >> other

    def set_upstream(self, other):
        self << other


def _chain(*items):
    for a, b in zip(items, items[1:]):
        a >> b


class _TriggerRule:
    ALL_SUCCESS, ALL_DONE, ONE_FAILED, ALL_FAILED = "all_success", "all_done", "one_failed", "all_failed"
    ONE_SUCCESS, NONE_FAILED, ALWAYS = "one_success", "none_failed", "always"


def _fake_modules():
    def op(name):
        return type(name, (FakeOperator,), {})

    spec = {
        "airflow": {"DAG": FakeDAG},
        "airflow.models": {"DAG": FakeDAG, "BaseOperator": FakeOperator},
        "airflow.models.baseoperator": {"chain": _chain, "BaseOperator": FakeOperator},
        "airflow.operators": {},
        "airflow.operators.python": {"PythonOperator": op("PythonOperator")},
        "airflow.operators.bash": {"BashOperator": op("BashOperator")},
        "airflow.operators.empty": {"EmptyOperator": op("EmptyOperator")},
        "airflow.sensors": {},
        "airflow.sensors.filesystem": {"FileSensor": op("FileSensor")},
        "airflow.utils": {},
        "airflow.utils.task_group": {"TaskGroup": FakeTaskGroup},
        "airflow.utils.trigger_rule": {"TriggerRule": _TriggerRule},
    }
    mods = {}
    for name, attrs in spec.items():
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        mods[name] = m
    return mods


@cache
def load_dag():
    path = ex.path(DAG_FILE)
    fakes = _fake_modules()
    saved = {k: sys.modules.get(k) for k in fakes}
    sys.modules.update(fakes)
    try:
        spec = importlib.util.spec_from_file_location("fake_dag_elt", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    dags = [v for v in vars(module).values() if isinstance(v, FakeDAG)]
    assert len(dags) == 1, "Tệp DAG phải tạo đúng một DAG ở top-level"
    return module, dags[0]


def ancestors(dag, task_id):
    seen, todo = set(), [task_id]
    while todo:
        for up in dag.tasks[todo.pop()].upstream:
            if up not in seen:
                seen.add(up)
                todo.append(up)
    return seen


# ---------------------------------------------------------------- test
def test_dag_settings_for_backfill():
    _, dag = load_dag()
    k = dag.kwargs
    assert dag.dag_id == "olist_elt"
    assert k.get("schedule") == "0 3 * * *"
    assert k.get("start_date") == datetime(2018, 1, 1)
    assert k.get("catchup") is True
    assert 1 <= k.get("max_active_runs", 16) <= 3
    da = dag.default_args
    assert da.get("retries", 0) >= 2
    assert isinstance(da.get("retry_delay"), timedelta)
    assert isinstance(da.get("execution_timeout"), timedelta)
    assert callable(da.get("on_failure_callback"))
    da["on_failure_callback"]({"ds": "2018-01-01", "task_instance": None, "dag": None, "exception": RuntimeError("x")})


def test_ingest_group_per_table():
    _, dag = load_dag()
    for t in TABLES:
        wait, load = dag.tasks[f"ingest.wait_{t}"], dag.tasks[f"ingest.load_{t}"]
        assert wait.kind == "FileSensor" and wait.args.get("mode") == "reschedule"
        assert "{{ ds" in wait.args.get("filepath", "")
        assert load.kind == "PythonOperator"
        assert load.upstream == {f"ingest.wait_{t}"}
    loads = {f"ingest.load_{t}" for t in TABLES}
    for a in loads:  # nạp song song: không load nào phụ thuộc load khác
        assert not (ancestors(dag, a) & loads)


def test_dbt_after_all_loads_then_quality_then_publish():
    _, dag = load_dag()
    dbt = dag.tasks["dbt_build"]
    assert dbt.kind == "BashOperator"
    cmd = dbt.args.get("bash_command", "")
    assert "dbt build" in cmd and "{{ ds }}" in cmd
    assert {f"ingest.load_{t}" for t in TABLES} <= ancestors(dag, "dbt_build")
    assert "dbt_build" in dag.tasks["quality_check"].upstream
    assert dag.tasks["quality_check"].kind == "PythonOperator"
    assert "quality_check" in dag.tasks["publish"].upstream


def test_alert_task_on_failure():
    _, dag = load_dag()
    alert = dag.tasks["alert_on_failure"]
    assert str(alert.args.get("trigger_rule")) in {"one_failed", "TriggerRule.ONE_FAILED"}
    assert {"dbt_build", "quality_check"} <= alert.upstream


def test_load_callable_receives_table():
    _, dag = load_dag()
    for t in TABLES:
        load = dag.tasks[f"ingest.load_{t}"]
        assert load.args.get("python_callable") is not None
        assert (load.args.get("op_kwargs") or {}).get("table") == t


def test_no_heavy_top_level_code():
    tree = ast.parse(ex.read(DAG_FILE))
    banned = {"connect", "read_csv", "read_parquet", "open", "get", "post", "now", "today", "days_ago"}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                name = sub.func.attr if isinstance(sub.func, ast.Attribute) else getattr(sub.func, "id", "")
                assert name not in banned, f"Top-level gọi {name}(): scheduler parse tệp DAG liên tục"


def test_real_airflow_dagbag():
    pytest.importorskip("airflow")
    from airflow.models import DagBag

    bag = DagBag(dag_folder=str(ex.path(DAG_FILE)), include_examples=False)
    assert not bag.import_errors
    assert "olist_elt" in bag.dags
