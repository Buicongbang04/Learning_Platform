"""Chạy `dbt build` (dbt-duckdb) trên bản sao project trong thư mục tạm: dữ liệu nhỏ, bản mart cố ý sai, dữ liệu thật."""
import json
import os
import shutil
import tempfile
import uuid
from functools import cache
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
PROFILES = """retail:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{db}"
      threads: 1
"""
COLUMNS = ["source_row", "Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
MART_COLUMNS = ["month", "revenue", "orders", "active_customers", "new_customers", "aov", "is_complete_month"]
# Bản mart "của team Marketing": bỏ khách vãng lai. Schema test vẫn đạt; chỉ test đối soát mới bắt được.
BUGGY_MART = """
select
    invoice_month as month,
    sum(revenue) as revenue,
    count(distinct invoice_no) as orders,
    count(distinct customer_id) as active_customers,
    0 as new_customers,
    sum(revenue) / count(distinct invoice_no) as aov,
    true as is_complete_month
from {{ ref('fct_sales_line') }}
where customer_id is not null
group by 1
"""


def load_retail_2010_2011() -> pd.DataFrame:
    """Bản chép của loader chuẩn (basic/02-retail-star-schema/tests): sheet Year 2010-2011 + source_row, cache parquet."""
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    st = xlsx.stat()
    cache_file = Path(tempfile.gettempdir()) / "da-cache" / f"m09_2010-2011_{st.st_mtime_ns}_{st.st_size}.parquet"
    if cache_file.exists():
        return pd.read_parquet(cache_file)
    df = pd.read_excel(xlsx, sheet_name="Year 2010-2011")
    df.insert(0, "source_row", range(1, len(df) + 1))
    for col in ["Invoice", "StockCode", "Description", "Country"]:
        df[col] = df[col].map(lambda x: None if pd.isna(x) else str(x))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_file.with_suffix(f".{uuid.uuid4().hex}.tmp")
    df.to_parquet(tmp)
    os.replace(tmp, cache_file)
    return df
WORKDIRS: list[Path] = []


@pytest.fixture(scope="module", autouse=True)
def _cleanup_workdirs():
    yield
    for work in WORKDIRS:
        shutil.rmtree(work, ignore_errors=True)


def small_raw() -> pd.DataFrame:
    nan = np.nan
    rows = [
        (1, "100", "A", "MUG", 2, "2011-01-05 10:00", 3.0, 1.0, "United Kingdom"),
        (2, "100", "B", "BOWL", 1, "2011-01-05 10:00", 10.0, 1.0, "United Kingdom"),
        (3, "101", "A", "MUG", 1, "2011-01-20 12:00", 3.0, nan, "France"),            # khách vãng lai
        (4, "C102", "A", "MUG", -1, "2011-01-21 09:00", 3.0, 1.0, "United Kingdom"),  # huỷ
        (5, "103", "A", "MUG", 4, "2011-02-02 09:00", 2.5, 2.0, "Germany"),
        (6, "104", "B", "BOWL", 1, "2011-02-10 11:00", 10.0, 1.0, "France"),           # khách 1 đổi quốc gia
        (7, "105", "C", "VASE", 3, "2011-02-11 11:00", 0.0, 2.0, "Germany"),           # giá 0
        (8, "106", "A", "MUG", 2, "2011-03-15 16:00", 3.0, 3.0, "United Kingdom"),
        (9, "106", "B", "BOWL", 1, "2011-03-15 16:00", 10.0, 3.0, "United Kingdom"),
        (10, "107", "B", "BOWL", -1, "2011-03-15 16:30", 10.0, 2.0, "Germany"),       # số lượng âm
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df


def build(raw: pd.DataFrame, mart_sql: str | None = None):
    """Chép project, nạp raw.sales_lines, chạy dbt build. Trả (project, db, kết quả dbt)."""
    from dbt.cli.main import dbtRunner

    work = Path(tempfile.mkdtemp(prefix="m09_dbt_"))
    WORKDIRS.append(work)
    project = work / "project"
    shutil.copytree(ex.path("dbt_project.yml").parent, project,
                    ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", "*.duckdb", "profiles.yml"))
    if mart_sql is not None:
        (project / "models" / "marts" / "mart_monthly_sales.sql").write_text(mart_sql, encoding="utf-8")
    db = work / "retail.duckdb"
    (work / "profiles.yml").write_text(PROFILES.format(db=db.as_posix()), encoding="utf-8")
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE SCHEMA raw")
        con.register("src", raw)
        con.execute("CREATE TABLE raw.sales_lines AS SELECT * FROM src")
    res = dbtRunner().invoke(["build", "--project-dir", str(project), "--profiles-dir", str(work), "--quiet",
                              "--target-path", str(work / "target"), "--log-path", str(work / "logs")])
    return work, db, res


def failures(res):
    return [(r.node.name, str(r.status), r.message) for r in (res.result or [])
            if str(r.status) not in ("success", "pass")]


def query(db, sql):
    with duckdb.connect(str(db)) as con:  # dbt-duckdb có thể còn giữ kết nối trong cùng tiến trình
        return con.execute(sql).fetchall()


@cache
def small():
    work, db, res = build(small_raw())
    assert res.success, f"dbt build lỗi: {failures(res) or res.exception}"
    return work, db


def test_staging_flags():
    _, db = small()
    got = query(db, "SELECT line_id, invoice_no, customer_id, is_cancellation, is_valid_sale FROM main.stg_sales_lines ORDER BY line_id")
    assert len(got) == 10, "Staging giữ mọi dòng nguồn (không lọc)"
    assert [r[4] for r in got] == [True, True, True, False, True, True, False, True, True, False]
    assert got[3][3] is True and got[2][2] is None and got[0][2] == 1


def test_fct_sales_line():
    _, db = small()
    got = query(db, """SELECT line_id, CAST(invoice_month AS VARCHAR), is_guest, revenue
                       FROM main.fct_sales_line ORDER BY line_id""")
    assert [r[0] for r in got] == [1, 2, 3, 5, 6, 8, 9]
    assert [r[1] for r in got] == ["2011-01-01"] * 3 + ["2011-02-01"] * 2 + ["2011-03-01"] * 2
    assert [r[2] for r in got] == [False, False, True, False, False, False, False]
    assert [r[3] for r in got] == pytest.approx([6.0, 10.0, 3.0, 10.0, 10.0, 6.0, 10.0])


def test_dim_customer():
    _, db = small()
    got = query(db, """SELECT customer_id, CAST(first_purchase_date AS VARCHAR), CAST(cohort_month AS VARCHAR), current_country
                       FROM main.dim_customer ORDER BY customer_id""")
    assert got == [
        (1, "2011-01-05", "2011-01-01", "France"),
        (2, "2011-02-02", "2011-02-01", "Germany"),
        (3, "2011-03-15", "2011-03-01", "United Kingdom"),
    ]


def test_mart_monthly_sales():
    _, db = small()
    cols = [r[0] for r in query(db, "DESCRIBE main.mart_monthly_sales")]
    assert cols == MART_COLUMNS
    got = query(db, "SELECT CAST(month AS VARCHAR), revenue, orders, active_customers, new_customers, aov, is_complete_month "
                    "FROM main.mart_monthly_sales ORDER BY month")
    assert [r[0] for r in got] == ["2011-01-01", "2011-02-01", "2011-03-01"]
    assert [r[1] for r in got] == pytest.approx([19.0, 20.0, 16.0])
    assert [r[2:5] for r in got] == [(2, 1, 1), (2, 2, 1), (1, 1, 1)]
    assert [r[5] for r in got] == pytest.approx([9.5, 10.0, 16.0])
    assert [r[6] for r in got] == [True, True, False], "Tháng 3 dừng ở 15/03: chưa đủ tháng"


def manifest(work):
    return json.loads((work / "target" / "manifest.json").read_text(encoding="utf-8"))


def test_tests_declared():
    work, _ = small()
    nodes = manifest(work)["nodes"].values()
    found = set()
    for n in nodes:
        if n["resource_type"] == "test" and "test_metadata" in n:
            found.add(((n.get("attached_node") or "").split(".")[-1], n.get("column_name"), n["test_metadata"]["name"]))
    need = {
        ("fct_sales_line", "line_id", "unique"), ("fct_sales_line", "line_id", "not_null"),
        ("fct_sales_line", "customer_id", "relationships"),
        ("dim_customer", "customer_id", "unique"), ("dim_customer", "customer_id", "not_null"),
        ("mart_monthly_sales", "month", "unique"), ("mart_monthly_sales", "month", "not_null"),
    }
    missing = need - found
    assert not missing, f"Thiếu data test: {sorted(missing)}"
    singular = [n for n in nodes if n["resource_type"] == "test" and "test_metadata" not in n
                and {"model.retail_mart.mart_monthly_sales", "model.retail_mart.fct_sales_line"} <= set(n["depends_on"]["nodes"])]
    assert singular, "Cần một singular test trong data_tests/ dùng ref() tới cả mart_monthly_sales và fct_sales_line"


def test_mart_documented():
    work, _ = small()
    mart = next(n for n in manifest(work)["nodes"].values() if n["resource_type"] == "model" and n["name"] == "mart_monthly_sales")
    assert "grain" in mart["description"].lower(), "Mô tả model phải nói grain"
    for col in MART_COLUMNS:
        desc = mart["columns"].get(col, {}).get("description", "")
        assert len(desc) >= 15 and "TODO" not in desc, f"Cột {col} cần mô tả (định nghĩa metric), hiện: {desc!r}"


def test_reconciliation_test_catches_buggy_mart():
    _, _, res = build(small_raw(), mart_sql=BUGGY_MART)
    failed = {name for name, status, _ in failures(res)}
    assert any(not name.startswith(("unique_", "not_null_", "accepted_values_", "relationships_")) for name in failed), (
        "Mart bỏ khách vãng lai (lệch 3 GBP so với fact) phải làm singular test đối soát FAIL; "
        f"các node lỗi: {sorted(failed) or 'không có'}")


def test_real_data_mart():
    work, db, res = build(load_retail_2010_2011())
    assert res.success, f"dbt build lỗi trên dữ liệu thật: {failures(res) or res.exception}"
    rows = {r[0]: r[1:] for r in query(db, """SELECT strftime(month, '%Y-%m'), revenue, orders, active_customers,
                                                     new_customers, aov, is_complete_month FROM main.mart_monthly_sales""")}
    assert len(rows) == 13
    nov, dec10, dec11 = rows["2011-11"], rows["2010-12"], rows["2011-12"]
    assert nov[0] == pytest.approx(1_509_496.33, abs=0.01) and nov[1:4] == (2_769, 1_664, 323)
    assert nov[4] == pytest.approx(545.14, abs=0.01) and nov[5] is True
    assert dec10[3] == 885 and dec10[2] == 885, "Tháng đầu dữ liệu: mọi khách đều 'mới'"
    assert dec11[5] is False and dec11[4] == pytest.approx(779.99, abs=0.01)
    assert sum(r[0] for r in rows.values()) == pytest.approx(10_666_702.54, abs=0.01)
    assert sum(r[3] for r in rows.values()) == 4_338
