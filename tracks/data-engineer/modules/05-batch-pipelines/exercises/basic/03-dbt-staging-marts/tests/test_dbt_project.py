"""Chạy `dbt build` trên một bản sao project trong thư mục tạm, đích là DuckDB."""

import json
import shutil
import tempfile
from functools import cache
from pathlib import Path

import duckdb
import pytest

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


@cache
def build():
    """Bước EL (nạp CSV vào schema raw) rồi dbt build. Trả về (thư mục project, kết quả dbt)."""
    from dbt.cli.main import dbtRunner

    work = Path(tempfile.mkdtemp(prefix="dbt_basic_"))
    project = work / "project"
    shutil.copytree(ex.path("dbt_project.yml").parent, project,
                    ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", "*.duckdb"))
    db = work / "olist.duckdb"
    (project / "profiles.yml").write_text(PROFILES.format(db=db.as_posix()), encoding="utf-8")

    con = duckdb.connect(str(db))
    con.execute("CREATE SCHEMA raw")
    for table in ["orders", "customers", "payments"]:
        csv = (ex.fixtures / f"{table}.csv").as_posix()
        con.execute(f"CREATE TABLE raw.{table} AS SELECT * FROM read_csv('{csv}', all_varchar=true)")
    con.close()

    res = dbtRunner().invoke(
        ["build", "--project-dir", str(project), "--profiles-dir", str(project), "--quiet"]
    )
    return project, db, res


def query(sql):
    _, db, _ = build()
    con = duckdb.connect(str(db))  # dbt-duckdb có thể còn giữ kết nối trong cùng process
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def test_dbt_build_succeeds():
    _, _, res = build()
    failed = [(r.node.name, str(r.status), r.message) for r in (res.result or []) if str(r.status) not in ("success", "pass")]
    assert res.success, f"dbt build lỗi: {failed or res.exception}"


def test_stg_orders_clean():
    rows = query("select order_id, order_status, order_date from main.stg_orders order by order_id")
    assert [r[0] for r in rows] == ["o1", "o2", "o3", "o4", "o5"]
    assert dict((r[0], r[1]) for r in rows)["o2"] == "delivered"
    assert str(rows[0][2]) == "2018-01-01"
    cols = [r[0] for r in query("describe main.stg_orders")]
    assert cols == ["order_id", "customer_id", "order_status", "purchased_at", "order_date"]


def test_fct_revenue_by_state():
    rows = query("select customer_state, orders, revenue from main.fct_revenue_by_state order by customer_state")
    assert [(s, o) for s, o, _ in rows] == [("RJ", 1), ("SP", 2)]
    revenue = {s: r for s, _, r in rows}
    assert revenue["SP"] == pytest.approx(150.0)
    assert revenue["RJ"] == pytest.approx(50.0)


def test_materializations():
    project, _, _ = build()
    manifest = json.loads((project / "target" / "manifest.json").read_text())
    mat = {n["name"]: n["config"]["materialized"] for n in manifest["nodes"].values() if n["resource_type"] == "model"}
    assert mat["stg_orders"] == "view"
    assert mat["fct_revenue_by_state"] == "table"
    fct = next(n for n in manifest["nodes"].values() if n["name"] == "fct_revenue_by_state")
    assert {"model.olist_basic.stg_orders", "model.olist_basic.stg_payments",
            "model.olist_basic.stg_customers"} <= set(fct["depends_on"]["nodes"]), "Dùng ref() thay vì tên bảng"


def test_schema_tests_declared():
    project, _, _ = build()
    manifest = json.loads((project / "target" / "manifest.json").read_text())
    found = set()
    for n in manifest["nodes"].values():
        if n["resource_type"] != "test" or "test_metadata" not in n:
            continue
        if n.get("attached_node") == "model.olist_basic.stg_orders":
            found.add((n["column_name"], n["test_metadata"]["name"]))
    assert {("order_id", "unique"), ("order_id", "not_null"),
            ("order_status", "accepted_values"), ("customer_id", "relationships")} <= found
