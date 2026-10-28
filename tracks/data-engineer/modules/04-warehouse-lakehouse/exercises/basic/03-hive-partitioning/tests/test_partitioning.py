import duckdb
import pyarrow.parquet as pq
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def part():
    return ex.module("partitioning.py")


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE orders AS
        SELECT
            'o' || lpad(i::VARCHAR, 5, '0') AS order_id,
            ['SP', 'RJ', 'MG'][i % 3 + 1] AS customer_state,
            CASE WHEN i % 7 = 0 THEN 'canceled' ELSE 'delivered' END AS order_status,
            TIMESTAMP '2023-11-01 08:00:00' + INTERVAL (i * 11) HOUR AS order_purchase_timestamp,
            round(10 + (i * 37) % 200 + 0.5, 2) AS payment_value
        FROM range(400) t(i)
        """
    )
    # 400 * 11h ≈ 183 ngày: 2023-11 .. 2024-05-03 -> cắt về 2024-04 cho gọn
    con.execute("DELETE FROM orders WHERE order_purchase_timestamp >= TIMESTAMP '2024-05-01'")
    yield con
    con.close()


def expected_by_month(con):
    return con.execute(
        """
        SELECT year(order_purchase_timestamp), month(order_purchase_timestamp), SUM(payment_value)
        FROM orders WHERE order_status = 'delivered' GROUP BY 1, 2 ORDER BY 1, 2
        """
    ).fetchall()


def test_layout(part, con, tmp_path):
    out = tmp_path / "orders"
    part.write_partitioned(con, "orders", out)
    assert (out / "year=2023" / "month=11").is_dir()
    assert part.list_partitions(out) == [(2023, 11), (2023, 12), (2024, 1), (2024, 2), (2024, 3), (2024, 4)]
    files = list(out.rglob("*.parquet"))
    assert files
    names = pq.read_schema(files[0]).names
    assert "year" not in names and "month" not in names


def test_rewrite_is_idempotent(part, con, tmp_path):
    out = tmp_path / "orders"
    part.write_partitioned(con, "orders", out)
    part.write_partitioned(con, "orders", out)
    total = con.execute(f"SELECT count(*) FROM read_parquet('{out}/**/*.parquet', hive_partitioning = true)").fetchone()[0]
    assert total == con.execute("SELECT count(*) FROM orders").fetchone()[0]


def test_monthly_revenue(part, con, tmp_path):
    out = tmp_path / "orders"
    part.write_partitioned(con, "orders", out)
    exp = {(y, m): r for y, m, r in expected_by_month(con)}
    assert part.monthly_revenue(con, out, 2024, 2) == pytest.approx(exp[(2024, 2)])
    assert part.monthly_revenue(con, out, 2023, 11) == pytest.approx(exp[(2023, 11)])


def test_revenue_by_month(part, con, tmp_path):
    out = tmp_path / "orders"
    part.write_partitioned(con, "orders", out)
    got = part.revenue_by_month(con, out)
    exp = expected_by_month(con)
    assert [(y, m) for y, m, _ in got] == [(y, m) for y, m, _ in exp]
    for (_, _, a), (_, _, b) in zip(got, exp):
        assert a == pytest.approx(b)
