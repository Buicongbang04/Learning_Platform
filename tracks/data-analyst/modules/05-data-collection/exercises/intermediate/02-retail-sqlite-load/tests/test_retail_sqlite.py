import uuid

import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa
from sqlalchemy import text

import testkit
from testkit import Exercise

ex = Exercise(__file__)
TABLE_COLUMNS = ["invoice", "stock_code", "description", "quantity", "invoice_date", "price", "customer_id",
                 "country"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("retail_sqlite.ipynb")


@pytest.fixture
def engine(nb, tmp_path):
    eng = sa.create_engine(f"sqlite:///{tmp_path / 'retail.sqlite'}")
    nb.create_schema(eng)
    yield eng
    eng.dispose()


def tiny():
    # tháng 1: hoá đơn 1 (2 dòng hợp lệ), C2 huỷ, 3 có một dòng giá 0; tháng 2: hoá đơn 4, một dòng số lượng âm
    return pd.DataFrame({
        "Invoice": [1, 1, "C2", 3, 3, 4, 4],
        "StockCode": [85123, "85123A", "POST", "22423", "22423", "84029G", "M"],
        "Description": ["A", "B", "POSTAGE", "C", "C", "D", "Manual"],
        "Quantity": [2, 3, -1, 4, 1, 5, -2],
        "InvoiceDate": pd.to_datetime(["2011-01-05 10:00", "2011-01-05 10:00", "2011-01-20 09:00",
                                       "2011-01-31 23:59", "2011-01-31 23:59", "2011-02-01 00:00",
                                       "2011-02-03 12:00"]),
        "Price": [10.0, 5.0, 8.0, 2.5, 0.0, 2.0, 1.0],
        "Customer ID": [17850.0, 17850.0, 17850.0, np.nan, np.nan, 13047.0, 13047.0],
        "Country": ["United Kingdom"] * 7,
    })


def count(engine, sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def test_to_table_types_and_names(nb):
    df = tiny()
    before = df.copy()
    out = nb.to_table(df)
    pd.testing.assert_frame_equal(df, before)
    assert list(out.columns) == TABLE_COLUMNS
    assert out["invoice"].tolist() == ["1", "1", "C2", "3", "3", "4", "4"]
    assert out["stock_code"].tolist()[:2] == ["85123", "85123A"]
    assert str(out["customer_id"].dtype) == "Int64"
    assert out["customer_id"].tolist()[0] == 17850 and pd.isna(out["customer_id"].iloc[3])
    assert pd.api.types.is_datetime64_any_dtype(out["invoice_date"])


def test_load_batch_inserts_and_logs(nb, engine):
    n = nb.load_batch(engine, tiny(), "2011", "online_retail_II.xlsx#Year 2010-2011", now=lambda: "T1")
    assert n == 7
    assert count(engine, "SELECT COUNT(*) FROM sales WHERE batch_id = '2011'") == 7
    with engine.connect() as conn:
        log = conn.execute(text("SELECT batch_id, source, n_rows, loaded_at FROM load_log")).fetchall()
    assert [tuple(r) for r in log] == [("2011", "online_retail_II.xlsx#Year 2010-2011", 7, "T1")]


def test_load_batch_is_idempotent(nb, engine):
    nb.load_batch(engine, tiny(), "2011", "src", now=lambda: "T1")
    nb.load_batch(engine, tiny(), "2011", "src", now=lambda: "T2")
    assert count(engine, "SELECT COUNT(*) FROM sales") == 7
    assert count(engine, "SELECT COUNT(*) FROM load_log") == 1
    assert count(engine, "SELECT loaded_at FROM load_log") == "T2"


def test_load_batch_replaces_only_its_batch(nb, engine):
    nb.load_batch(engine, tiny(), "a", "src", now=lambda: "T1")
    nb.load_batch(engine, tiny(), "b", "src", now=lambda: "T1")
    nb.load_batch(engine, tiny().head(2), "a", "src", now=lambda: "T2")
    assert count(engine, "SELECT COUNT(*) FROM sales WHERE batch_id = 'a'") == 2
    assert count(engine, "SELECT COUNT(*) FROM sales WHERE batch_id = 'b'") == 7


def test_load_batch_failure_keeps_old_data(nb, engine):
    nb.load_batch(engine, tiny(), "a", "src", now=lambda: "T1")
    broken = tiny()
    broken["Description"] = broken["Description"].astype(object)
    broken.at[5, "Description"] = {"không": "ghi được vào SQL"}  # lỗi xảy ra lúc INSERT, sau khi đã DELETE
    with pytest.raises(Exception):
        nb.load_batch(engine, broken, "a", "src", now=lambda: "T2")
    assert count(engine, "SELECT COUNT(*) FROM sales WHERE batch_id = 'a'") == 7
    assert count(engine, "SELECT loaded_at FROM load_log WHERE batch_id = 'a'") == "T1"


def test_monthly_revenue(nb, engine):
    nb.load_batch(engine, tiny(), "2011", "src", now=lambda: "T1")
    out = nb.monthly_revenue(engine, "2011-01-01", "2011-03-01")
    assert list(out.columns) == ["month", "revenue", "invoices"]
    assert out["month"].tolist() == ["2011-01", "2011-02"]
    # tháng 1: 20 + 15 + 10 (dòng giá 0 và hoá đơn huỷ bị bỏ); tháng 2: 10 (dòng số lượng âm bị bỏ)
    assert out["revenue"].tolist() == pytest.approx([45.0, 10.0])
    assert out["invoices"].tolist() == [2, 1]
    feb = nb.monthly_revenue(engine, "2011-02-01", "2011-03-01")
    assert feb["month"].tolist() == ["2011-02"]


def test_monthly_revenue_binds_parameters(nb, engine):
    nb.load_batch(engine, tiny(), "2011", "src", now=lambda: "T1")
    # giá trị có dấu nháy: nếu ghép chuỗi vào SQL sẽ lỗi cú pháp (hoặc tệ hơn, SQL injection)
    out = nb.monthly_revenue(engine, "2010-12-01'", "2012-01-01")
    assert isinstance(out, pd.DataFrame)


def test_reconcile(nb, engine):
    df = tiny()
    nb.load_batch(engine, df, "2011", "src", now=lambda: "T1")
    res = nb.reconcile(engine, df, "2011")
    assert res == {"rows_source": 7, "rows_db": 7, "revenue_source": pytest.approx(55.0),
                   "revenue_db": pytest.approx(55.0), "ok": True}
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sales WHERE invoice = '4'"))
    res = nb.reconcile(engine, df, "2011")
    assert res["rows_db"] == 5 and res["revenue_db"] == pytest.approx(45.0) and res["ok"] is False


@pytest.fixture(scope="module")
def real_head():
    path = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    return pd.read_excel(path, sheet_name="Year 2010-2011", nrows=20_000,
                         dtype={"Invoice": str, "StockCode": str, "Description": str})


def test_real_first_rows(nb, engine, real_head):
    n = nb.load_batch(engine, real_head, "2010-2011-head", "online_retail_II.xlsx#Year 2010-2011 (20 000 dòng đầu)")
    assert n == 20_000
    out = nb.monthly_revenue(engine, "2010-12-01", "2011-01-01")
    assert out["month"].tolist() == ["2010-12"]
    assert out["revenue"].iloc[0] == pytest.approx(399_971.28, abs=0.01)
    assert out["invoices"].iloc[0] == 756
    assert nb.reconcile(engine, real_head, "2010-2011-head")["ok"] is True


def test_postgres_same_code(nb):
    """Cùng hàm, đổi URL sang Postgres: tự skip khi chưa bật dịch vụ postgres."""
    ex.require_service("postgres")
    url = testkit.POSTGRES_DSN.replace("postgresql://", "postgresql+psycopg://", 1)
    schema = f"m05_test_{uuid.uuid4().hex[:8]}"
    admin = sa.create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema}"))
    eng = sa.create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        nb.create_schema(eng)
        nb.load_batch(eng, tiny(), "2011", "src", now=lambda: "T1")
        nb.load_batch(eng, tiny(), "2011", "src", now=lambda: "T2")
        out = nb.monthly_revenue(eng, "2011-01-01", "2011-03-01")
        assert out["month"].tolist() == ["2011-01", "2011-02"]
        assert out["revenue"].tolist() == pytest.approx([45.0, 10.0])
        assert nb.reconcile(eng, tiny(), "2011")["ok"] is True
    finally:
        eng.dispose()
        with admin.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()
