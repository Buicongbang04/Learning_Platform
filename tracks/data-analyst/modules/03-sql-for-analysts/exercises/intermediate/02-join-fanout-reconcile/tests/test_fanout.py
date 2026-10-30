from pathlib import Path

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

DH_TABLES = ("transaction_data", "hh_demographic", "campaign_table", "campaign_desc")


def load_dunnhumby(con: duckdb.DuckDBPyConnection, folder: Path) -> None:
    """Bốn bảng dunnhumby, tên bảng và tên cột giữ nguyên như tệp CSV."""
    for table in DH_TABLES:
        path = str(folder / f"{table}.csv").replace("'", "''")
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv('{path}', header = true)")


TX_COLUMNS = ("household_key BIGINT, BASKET_ID BIGINT, DAY BIGINT, PRODUCT_ID BIGINT, QUANTITY BIGINT, "
              "SALES_VALUE DOUBLE, STORE_ID BIGINT, RETAIL_DISC DOUBLE, TRANS_TIME VARCHAR, WEEK_NO BIGINT, "
              "COUPON_DISC DOUBLE, COUPON_MATCH_DISC DOUBLE")
DEMO_COLUMNS = ("AGE_DESC VARCHAR, MARITAL_STATUS_CODE VARCHAR, INCOME_DESC VARCHAR, HOMEOWNER_DESC VARCHAR, "
                "HH_COMP_DESC VARCHAR, HOUSEHOLD_SIZE_DESC VARCHAR, KID_CATEGORY_DESC VARCHAR, household_key BIGINT")


def tx(household, value, qty=1, basket=1):
    return (household, basket, 10, 100, qty, value, 1, 0.0, "1200", 2, 0.0, 0.0)


def demo(household, income):
    return ("45-54", "A", income, "Homeowner", "2 Adults No Kids", "2", "None/Unknown", household)


TRANSACTIONS = [
    tx(1, 10.0), tx(1, 20.0, basket=2),
    tx(1, 0.0),            # SALES_VALUE = 0: không phải dòng doanh thu hợp lệ
    tx(1, 5.0, qty=0),     # QUANTITY = 0: không hợp lệ
    tx(2, 50.0, basket=3),
    tx(3, 15.0, basket=4),
    tx(4, 5.0, basket=5),  # hộ không có nhân khẩu học, không nhận campaign
    tx(5, 0.0, basket=6),  # hộ chỉ có dòng 0: không tính là hộ có doanh thu
]
DEMOGRAPHICS = [demo(1, "50-74K"), demo(2, "50-74K"), demo(3, "Under 15K"), demo(7, "100-124K")]
CAMPAIGN_TABLE = [  # DESCRIPTION, household_key, CAMPAIGN
    ("TypeA", 1, 1), ("TypeA", 1, 2), ("TypeB", 1, 3), ("TypeA", 2, 1),
    ("TypeC", 6, 4),  # hộ 6 nhận campaign nhưng không có giao dịch
    ("TypeB", 3, 3), ("TypeB", 3, 5),
]
CAMPAIGN_DESC = [("TypeA", 1, 1, 30), ("TypeA", 2, 10, 40), ("TypeB", 3, 5, 50), ("TypeC", 4, 20, 60), ("TypeB", 5, 30, 70)]


@pytest.fixture
def small():
    con = duckdb.connect()
    con.execute(f"CREATE TABLE transaction_data ({TX_COLUMNS})")
    con.execute(f"CREATE TABLE hh_demographic ({DEMO_COLUMNS})")
    con.execute("CREATE TABLE campaign_table (DESCRIPTION VARCHAR, household_key BIGINT, CAMPAIGN BIGINT)")
    con.execute("CREATE TABLE campaign_desc (DESCRIPTION VARCHAR, CAMPAIGN BIGINT, START_DAY BIGINT, END_DAY BIGINT)")
    con.executemany(f"INSERT INTO transaction_data VALUES ({', '.join(['?'] * 12)})", TRANSACTIONS)
    con.executemany(f"INSERT INTO hh_demographic VALUES ({', '.join(['?'] * 8)})", DEMOGRAPHICS)
    con.executemany("INSERT INTO campaign_table VALUES (?, ?, ?)", CAMPAIGN_TABLE)
    con.executemany("INSERT INTO campaign_desc VALUES (?, ?, ?, ?)", CAMPAIGN_DESC)
    yield con
    con.close()


@pytest.fixture(scope="module")
def real():
    folder = ex.dataset("dunnhumby-complete-journey")
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    load_dunnhumby(con, folder)
    yield con
    con.close()


def run(con, name):
    rel = con.execute(ex.read(name))
    return [d[0] for d in rel.description], rel.fetchall()


def floats(row):
    return [float(x) for x in row]


def test_fanout_audit_small(small):
    cols, rows = run(small, "fanout_audit.sql")
    assert cols == ["valid_rows", "joined_rows", "fanout_factor", "revenue_true", "revenue_naive", "inflation_factor"]
    assert len(rows) == 1
    assert floats(rows[0]) == pytest.approx([5, 9, 1.8, 100.0, 170.0, 1.7], abs=0.01)


def test_campaign_type_revenue_small(small):
    cols, rows = run(small, "campaign_type_revenue.sql")
    assert cols == ["campaign_type", "households", "revenue", "revenue_per_household"]
    got = [(t, int(h), float(r), float(p)) for t, h, r, p in rows]
    assert got == [
        ("None", 1, pytest.approx(5.0), pytest.approx(5.0)),
        ("TypeA", 2, pytest.approx(80.0), pytest.approx(40.0)),   # hộ 1 nhận 2 campaign TypeA: chỉ tính 1 lần
        ("TypeB", 2, pytest.approx(45.0), pytest.approx(22.5)),
        ("TypeC", 1, pytest.approx(0.0), pytest.approx(0.0)),     # hộ nhận campaign mà không mua: vẫn đếm, doanh thu 0
    ]


def test_revenue_by_income_small(small):
    cols, rows = run(small, "revenue_by_income.sql")
    assert cols == ["income_desc", "households", "revenue", "share"]
    got = [(i, int(h), float(r), float(s)) for i, h, r, s in rows]
    assert got == [
        ("50-74K", 2, pytest.approx(80.0), pytest.approx(0.8, abs=1e-4)),
        ("Under 15K", 1, pytest.approx(15.0), pytest.approx(0.15, abs=1e-4)),
        ("Unknown", 1, pytest.approx(5.0), pytest.approx(0.05, abs=1e-4)),   # hộ không có nhân khẩu học vẫn có mặt
    ]


CHECKS = ["income_revenue_total", "income_households_total", "campaign_households_total", "naive_join_revenue_total"]


def test_reconcile_small(small):
    cols, rows = run(small, "reconcile.sql")
    assert cols == ["check_name", "expected", "actual", "passed"]
    assert [row[0] for row in rows] == CHECKS
    assert [floats(row[1:3]) for row in rows] == [
        pytest.approx([100.0, 100.0]), pytest.approx([4, 4]), pytest.approx([4, 4]), pytest.approx([100.0, 170.0]),
    ]
    assert [row[3] for row in rows] == [True, True, True, False]


def test_real_fanout_audit(real):
    _, rows = run(real, "fanout_audit.sql")
    valid, joined, fanout, true_rev, naive_rev, inflation = floats(rows[0])
    assert (valid, joined) == (2_576_815, 13_919_433)
    assert fanout == pytest.approx(5.40, abs=0.01) and inflation == pytest.approx(5.44, abs=0.01)
    assert true_rev == pytest.approx(8_057_443.80, abs=0.01)
    assert naive_rev == pytest.approx(43_835_274.72, abs=0.05)


def test_real_campaign_type_revenue(real):
    _, rows = run(real, "campaign_type_revenue.sql")
    got = {t: (int(h), float(r)) for t, h, r, _ in rows}
    assert got["None"] == (916, pytest.approx(942_143.58, abs=0.01))
    assert got["TypeA"] == (1513, pytest.approx(6_935_414.78, abs=0.01))
    assert got["TypeB"][0] == 1023 and got["TypeC"][0] == 397


def test_real_revenue_by_income(real):
    _, rows = run(real, "revenue_by_income.sql")
    assert len(rows) == 13
    assert rows[0][0] == "Unknown" and int(rows[0][1]) == 1699
    assert float(rows[0][3]) == pytest.approx(0.4418, abs=1e-4)
    assert rows[1][0] == "50-74K"
    assert sum(int(row[1]) for row in rows) == 2500
    assert sum(float(row[2]) for row in rows) == pytest.approx(8_057_443.80, abs=0.05)


def test_real_reconcile(real):
    _, rows = run(real, "reconcile.sql")
    assert [row[0] for row in rows] == CHECKS
    assert [row[3] for row in rows] == [True, True, True, False]
    assert float(rows[1][1]) == 2500 and float(rows[3][2]) == pytest.approx(43_835_274.72, abs=0.05)
