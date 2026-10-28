import json

import duckdb
import pytest
import yaml

from testkit import Exercise, use_solution

if use_solution():
    pytest.skip("Bài advanced chỉ có SOLUTION.md (hướng làm + rubric), không có code mẫu", allow_module_level=True)

ex = Exercise(__file__)

HEADER = "order_id,customer_id,order_status,amount,order_purchase_timestamp\n"
DAYS = {
    "2018-01-01": [
        "o1,c1,delivered,10.5,2018-01-01 10:00:00",
        "o2,c2,shipped,20,2018-01-01 11:00:00",
        "o3,c3,delivered,30,2018-01-01 12:00:00",
        "o4,c4,delivered,40,2018-01-01 13:00:00",
        "o5,c5,lost,50,2018-01-01 14:00:00",  # status ngoài enum
    ],
    "2018-01-02": [
        "o6,c1,delivered,5,2018-01-02 09:00:00",
        "o6,c1,delivered,5,2018-01-02 09:00:00",  # trùng order_id
        "o7,c2,created,7,2018-01-02 10:00:00",
        "o8,c3,approved,8,2018-01-02 11:00:00",
        "o9,c4,delivered,9,2018-01-02 12:00:00",
        "o10,c5,delivered,10,2018-01-02 13:00:00",
    ],
    # 2018-01-03 không có file
    "2018-01-04": [
        ",c1,delivered,1,2018-01-04 09:00:00",  # thiếu order_id
        "o11,c2,delivered,-3,2018-01-04 10:00:00",  # amount âm
        "o12,c3,delivered,abc,2018-01-04 11:00:00",  # amount không phải số
        "o13,,delivered,4,not-a-date",  # thiếu customer_id + timestamp sai
        "o14,c5,delivered,5,2018-01-04 12:00:00",
    ],
}


@pytest.fixture
def env(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for ds, lines in DAYS.items():
        (raw / f"orders_{ds}.csv").write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return str(raw), str(tmp_path / "wh.duckdb"), str(ex.path("contract.yml"))


def q(db, sql):
    con = duckdb.connect(db)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def test_contract_file_complete():
    c = yaml.safe_load(ex.read("contract.yml"))
    cols = c["columns"]
    assert cols["order_id"].get("required") and cols["order_id"].get("unique")
    assert cols["customer_id"].get("required")
    assert set(cols["order_status"]["enum"]) == {"created", "approved", "shipped", "delivered", "canceled"}
    assert cols["amount"]["type"] == "number" and cols["amount"]["min"] == 0
    assert cols["order_purchase_timestamp"]["type"] == "timestamp"
    assert cols["order_purchase_timestamp"].get("required")


def test_validate_rules(env):
    p = ex.module("pipeline.py")
    contract = p.load_contract(env[2])
    rows = [dict(zip(HEADER.strip().split(","), line.split(","))) for line in DAYS["2018-01-04"]]
    good, bad = p.validate(rows, contract)
    assert [r["order_id"] for r in good] == ["o14"]
    assert good[0]["amount"] == 5.0
    assert good[0]["order_purchase_timestamp"].year == 2018
    reasons = {r["order_id"]: r["_reason"] for r in bad}
    assert "order_id" in reasons[""]
    assert "amount" in reasons["o11"] and "amount" in reasons["o12"]
    assert len(bad) == 4


def test_backfill_with_quarantine_and_errors(env):
    p = ex.module("pipeline.py")
    raw, db, contract = env
    out = p.backfill(raw, db, "2018-01-01", "2018-01-04", contract, max_error_rate=0.2)
    by_ds = {r["ds"]: r for r in out}
    assert [r["ds"] for r in out] == ["2018-01-01", "2018-01-02", "2018-01-03", "2018-01-04"]
    assert by_ds["2018-01-01"]["loaded"] == 4 and by_ds["2018-01-01"]["quarantined"] == 1
    assert by_ds["2018-01-02"]["loaded"] == 5 and by_ds["2018-01-02"]["quarantined"] == 1
    assert "error" in by_ds["2018-01-03"]  # thiếu file
    assert "error" in by_ds["2018-01-04"]  # 80% dòng lỗi > 20%
    counts = dict(q(db, "SELECT CAST(ds AS VARCHAR), count(*) FROM fct_orders GROUP BY ds"))
    assert counts == {"2018-01-01": 4, "2018-01-02": 5}
    reasons = q(db, "SELECT reason FROM quarantine_orders WHERE ds = DATE '2018-01-01'")
    assert len(reasons) == 1 and "order_status" in reasons[0][0]
    row = json.loads(q(db, "SELECT row_json FROM quarantine_orders WHERE ds = DATE '2018-01-02'")[0][0])
    assert row["order_id"] == "o6"


def test_backfill_is_idempotent(env):
    p = ex.module("pipeline.py")
    raw, db, contract = env
    p.backfill(raw, db, "2018-01-01", "2018-01-04", contract)
    before = q(db, "SELECT count(*), sum(amount) FROM fct_orders") + q(db, "SELECT count(*) FROM quarantine_orders")
    p.backfill(raw, db, "2018-01-01", "2018-01-04", contract)
    after = q(db, "SELECT count(*), sum(amount) FROM fct_orders") + q(db, "SELECT count(*) FROM quarantine_orders")
    assert before == after


def test_violation_keeps_previous_partition(env, tmp_path):
    p = ex.module("pipeline.py")
    raw, db, contract = env
    p.run_partition(raw, db, "2018-01-01", contract)
    # Lần giao lại file của ngày 01 bị hỏng nặng -> không được ghi đè dữ liệu tốt đang có
    (tmp_path / "raw" / "orders_2018-01-01.csv").write_text(
        HEADER + "x1,c1,lost,1,2018-01-01 10:00:00\nx2,c1,lost,1,2018-01-01 10:00:00\n", encoding="utf-8"
    )
    with pytest.raises(p.ContractViolation):
        p.run_partition(raw, db, "2018-01-01", contract)
    ids = sorted(r[0] for r in q(db, "SELECT order_id FROM fct_orders WHERE ds = DATE '2018-01-01'"))
    assert ids == ["o1", "o2", "o3", "o4"]
