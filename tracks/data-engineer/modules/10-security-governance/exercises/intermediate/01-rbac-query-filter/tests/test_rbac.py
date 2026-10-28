import hashlib

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

ADMIN = {"name": "ana", "role": "admin"}
ANALYST = {"name": "bruno", "role": "analyst"}
SELLER_A = {"name": "loja-a", "role": "seller", "seller_id": "s_a"}
SELLER_B = {"name": "loja-b", "role": "seller", "seller_id": "s_b"}


@pytest.fixture(scope="module")
def rbac():
    return ex.module("rbac.py")


@pytest.fixture()
def con():
    c = duckdb.connect()
    c.execute("""
        CREATE TABLE order_items AS SELECT * FROM (VALUES
          ('o1', 1, 'p1', 's_a', 100.0, 10.0, 'ana@gmail.com',  '529.982.247-25'),
          ('o1', 2, 'p2', 's_b',  50.0,  5.0, 'ana@gmail.com',  '529.982.247-25'),
          ('o2', 1, 'p1', 's_a', 100.0, 12.0, 'joao@uol.com.br', '123.456.789-09'),
          ('o3', 1, 'p3', 's_c',  30.0,  3.0, 'lia@gmail.com',  '987.654.321-00')
        ) t(order_id, order_item_id, product_id, seller_id, price, freight_value, customer_email, customer_cpf)
    """)
    yield c
    c.close()


def test_allowed_columns(rbac):
    assert rbac.allowed_columns("admin", "order_items", ["*"]) == rbac.TABLE_COLUMNS["order_items"]
    assert "customer_cpf" not in rbac.allowed_columns("analyst", "order_items", ["*"])
    assert rbac.allowed_columns("seller", "order_items", ["price", "order_id"]) == ["price", "order_id"]
    with pytest.raises(PermissionError):
        rbac.allowed_columns("analyst", "order_items", ["customer_cpf"])
    with pytest.raises(PermissionError):
        rbac.allowed_columns("seller", "order_items", ["customer_email"])
    with pytest.raises(PermissionError):
        rbac.allowed_columns("intern", "order_items", ["order_id"])
    with pytest.raises(PermissionError):
        rbac.allowed_columns("admin", "payments", ["*"])
    with pytest.raises(PermissionError):
        rbac.allowed_columns("admin", "order_items", ["price; DROP TABLE order_items"])


def test_build_query_is_parameterized(rbac):
    sql, params = rbac.build_query(SELLER_A, "order_items", ["order_id", "price"], {"product_id": "p1"})
    assert "s_a" not in sql and "p1" not in sql
    assert params == ["s_a", "p1"]
    assert sql.count("?") == 2


def test_admin_sees_everything(rbac, con):
    df = rbac.run_query(con, ADMIN, "order_items", ["*"])
    assert len(df) == 4
    assert "529.982.247-25" in df["customer_cpf"].tolist()


def test_analyst_masked_email(rbac, con):
    df = rbac.run_query(con, ANALYST, "order_items", ["order_id", "customer_email"])
    assert len(df) == 4
    assert "ana@gmail.com" not in df["customer_email"].tolist()
    assert df["customer_email"].iloc[0] == hashlib.md5(b"ana@gmail.com").hexdigest()
    # vẫn đếm được khách unique
    assert df["customer_email"].nunique() == 3
    with pytest.raises(PermissionError):
        rbac.run_query(con, ANALYST, "order_items", ["customer_cpf"])
    with pytest.raises(PermissionError):
        # không cho lọc theo cột bị che để dò email
        rbac.run_query(con, ANALYST, "order_items", ["order_id"], {"customer_email": "ana@gmail.com"})


def test_seller_row_level_security(rbac, con):
    a = rbac.run_query(con, SELLER_A, "order_items", ["*"])
    assert set(a["seller_id"]) == {"s_a"} and len(a) == 2
    assert "customer_email" not in a.columns
    b = rbac.run_query(con, SELLER_B, "order_items", ["order_id", "price"])
    assert b["order_id"].tolist() == ["o1"]
    # cố lọc sang seller khác vẫn không thấy gì
    assert len(rbac.run_query(con, SELLER_A, "order_items", ["order_id"], {"seller_id": "s_c"})) == 0
    with pytest.raises(PermissionError):
        rbac.run_query(con, {"role": "seller"}, "order_items", ["order_id"])


def test_sql_injection_value(rbac, con):
    df = rbac.run_query(con, SELLER_A, "order_items", ["order_id"], {"product_id": "' OR 1=1 --"})
    assert len(df) == 0
    assert con.execute("SELECT count(*) FROM order_items").fetchone()[0] == 4
