import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def q():
    return ex.module("quality.py")


def clean_orders():
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3"],
        "customer_id": ["c1", "c2", "c3"],
        "order_status": ["delivered", "shipped", "canceled"],
        "order_purchase_timestamp": ["2018-01-01 10:00", "2018-01-02 11:00", "2018-01-03 12:00"],
        "order_delivered_customer_date": ["2018-01-05 09:00", None, None],
        "price": [59.9, 120.0, 15.5],
        "freight_value": [10.0, 0.0, 7.2],
        "extra_col": [1, 2, 3],
    })


def dirty_orders():
    df = pd.DataFrame({
        "order_id": ["o1", "o1", None, "o4", "o5", "o6"],
        "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6"],
        "order_status": ["delivered", "shipped", "shipped", "lost", "delivered", "delivered"],
        "order_purchase_timestamp": ["2018-01-01", "2018-01-02", "2018-01-03", "2018-01-04",
                                     "2018-01-10", "2018-01-06"],
        "order_delivered_customer_date": ["2018-01-03", None, None, None, "2018-01-08", "2018-01-09"],
        "price": [10.0, 20.0, 30.0, -5.0, 50.0, 60.0],
        "freight_value": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    })
    return df


def test_schema_type(q):
    import pandera.pandas as pa
    schema = q.build_orders_schema()
    assert isinstance(schema, pa.DataFrameSchema)
    assert {"order_id", "order_status", "price", "freight_value",
            "order_purchase_timestamp", "order_delivered_customer_date"} <= set(schema.columns)


def test_clean_data_passes(q):
    valid, failures = q.validate(clean_orders())
    assert len(valid) == 3
    assert len(failures) == 0
    assert set(q.FAILURE_COLUMNS) <= set(failures.columns)


def test_dirty_data_quarantined(q):
    df = dirty_orders()
    valid, failures = q.validate(df)
    # chỉ dòng o6 (index 5) sạch
    assert list(valid.index) == [5]
    assert valid["order_id"].tolist() == ["o6"]
    checks = " ".join(failures["check"].astype(str))
    assert "delivered_after_purchase" in checks
    assert "isin" in checks
    assert "not_nullable" in checks
    assert "uniqueness" in checks or "unique" in checks
    assert "greater_than" in checks


def test_quality_report(q):
    rep = q.quality_report(dirty_orders())
    assert rep["rows"] == 6
    assert rep["valid_rows"] == 1
    assert rep["invalid_rows"] == 5
    fc = rep["failed_checks"]
    assert fc["delivered_after_purchase"] == 1
    assert sum(v for k, v in fc.items() if k.startswith("isin")) == 1
    assert fc["not_nullable"] == 1
    clean = q.quality_report(clean_orders())
    assert clean == {"rows": 3, "valid_rows": 3, "invalid_rows": 0, "failed_checks": {}}
