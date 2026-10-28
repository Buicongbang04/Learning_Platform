"""Hai lượt `dbt build`: lượt 1 trên dữ liệu ban đầu, lượt 2 sau khi nguồn thay đổi."""

import json
import shutil
import tempfile
from functools import cache
from pathlib import Path

import duckdb

from testkit import Exercise

ex = Exercise(__file__)

PROFILES = """olist:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{db}"
      threads: 1
"""

ORDERS_V1 = [
    ("o1", "c1", "created", "10", "2018-01-01 10:00:00"),
    ("o2", "c2", "created", "20", "2018-01-01 11:00:00"),
    ("o3", "c1", "delivered", "30", "2018-01-01 12:00:00"),
]
CUSTOMERS_V1 = [
    ("c1", "sao paulo", "SP", "2018-01-01 00:00:00"),
    ("c2", "rio de janeiro", "RJ", "2018-01-01 00:00:00"),
]


def sql(db, statements, fetch=None):
    con = duckdb.connect(str(db))
    try:
        for s, params in statements:
            con.execute(s, params) if params else con.execute(s)
        return con.execute(fetch).fetchall() if fetch else None
    finally:
        con.close()


def dbt_build(project):
    from dbt.cli.main import dbtRunner

    res = dbtRunner().invoke(["build", "--project-dir", str(project), "--profiles-dir", str(project), "--quiet"])
    if not res.success:
        failed = [(r.node.name, str(r.status), r.message) for r in (res.result or []) if str(r.status) not in ("success", "pass")]
        raise AssertionError(f"dbt build lỗi: {failed or res.exception}")
    return res


@cache
def scenario():
    work = Path(tempfile.mkdtemp(prefix="dbt_incr_"))
    project = work / "project"
    shutil.copytree(ex.path("dbt_project.yml").parent, project,
                    ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", "*.duckdb"))
    db = work / "olist.duckdb"
    (project / "profiles.yml").write_text(PROFILES.format(db=db.as_posix()), encoding="utf-8")

    stmts = [
        ("CREATE SCHEMA raw", None),
        ("CREATE TABLE raw.orders (order_id VARCHAR, customer_id VARCHAR, order_status VARCHAR, amount VARCHAR, updated_at VARCHAR)", None),
        ("CREATE TABLE raw.customers (customer_id VARCHAR, customer_city VARCHAR, customer_state VARCHAR, updated_at VARCHAR)", None),
    ]
    stmts += [("INSERT INTO raw.orders VALUES (?, ?, ?, ?, ?)", list(r)) for r in ORDERS_V1]
    stmts += [("INSERT INTO raw.customers VALUES (?, ?, ?, ?)", list(r)) for r in CUSTOMERS_V1]
    sql(db, stmts)
    dbt_build(project)
    after_first = sql(db, [], "SELECT order_id, order_status FROM main.fct_orders ORDER BY order_id")

    sql(db, [
        ("UPDATE raw.orders SET order_status = 'delivered', updated_at = '2018-01-02 09:00:00' WHERE order_id = 'o1'", None),
        ("INSERT INTO raw.orders VALUES ('o4', 'c2', 'created', '40', '2018-01-02 10:00:00')", None),
        # Dòng có updated_at cũ hơn mốc đã nạp: incremental theo updated_at sẽ KHÔNG thấy nó.
        ("INSERT INTO raw.orders VALUES ('o0', 'c2', 'created', '5', '2018-01-01 08:00:00')", None),
        ("UPDATE raw.customers SET customer_city = 'campinas', updated_at = '2018-01-02 00:00:00' WHERE customer_id = 'c1'", None),
    ])
    dbt_build(project)
    return project, db, after_first


def test_first_build():
    _, _, after_first = scenario()
    assert after_first == [("o1", "created"), ("o2", "created"), ("o3", "delivered")]


def test_incremental_merges_updates_and_new_rows():
    _, db, _ = scenario()
    rows = sql(db, [], "SELECT order_id, order_status, amount FROM main.fct_orders ORDER BY order_id")
    assert rows == [("o1", "delivered", 10.0), ("o2", "created", 20.0), ("o3", "delivered", 30.0), ("o4", "created", 40.0)]


def test_incremental_really_is_incremental():
    _, db, _ = scenario()
    ids = [r[0] for r in sql(db, [], "SELECT order_id FROM main.fct_orders")]
    assert "o0" not in ids, "Model đang build lại toàn bộ (table), chưa lọc bằng is_incremental()"


def test_model_config():
    project, _, _ = scenario()
    manifest = json.loads((project / "target" / "manifest.json").read_text())
    node = manifest["nodes"]["model.olist_incremental.fct_orders"]
    assert node["config"]["materialized"] == "incremental"
    assert node["config"]["unique_key"] == "order_id"


def test_snapshot_keeps_history():
    _, db, _ = scenario()
    rows = sql(db, [], """
        SELECT customer_id, customer_city, dbt_valid_to IS NULL AS is_current
        FROM snapshots.customers_snapshot
        ORDER BY customer_id, dbt_valid_from
    """)
    assert rows == [
        ("c1", "sao paulo", False),
        ("c1", "campinas", True),
        ("c2", "rio de janeiro", True),
    ]
