import re
from datetime import date, datetime

import pytest

from testkit import Exercise

ex = Exercise(__file__)

KEYSPACE = "de_ex03_query_model"


# ---------- Parser CQL tối giản để kiểm tra schema offline ----------

def _balanced(text: str, start: int) -> tuple[str, int]:
    """text[start] là '('; trả nội dung bên trong và vị trí sau ')'."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
    raise ValueError("Ngoặc không cân bằng")


def _split_top(text: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def parse_cql(cql: str) -> dict:
    text = re.sub(r"(--|//)[^\n]*", "", cql)
    tables = {}
    for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?(\w+)\s*\(", text, re.I):
        name = m.group(1).lower()
        body, end = _balanced(text, m.end() - 1)
        rest = text[end : text.find(";", end) if ";" in text[end:] else len(text)]
        columns, partition, clustering = {}, [], []
        for part in _split_top(body):
            pk = re.match(r"PRIMARY\s+KEY\s*\((.*)\)\s*$", part, re.I | re.S)
            if pk:
                items = _split_top(pk.group(1))
                first = items[0]
                if first.startswith("("):
                    partition = [c.strip().lower() for c in first.strip("()").split(",")]
                else:
                    partition = [first.lower()]
                clustering = [c.strip().lower() for c in items[1:]]
                continue
            tokens = part.split()
            if len(tokens) >= 2:
                columns[tokens[0].lower()] = tokens[1].lower()
                if re.search(r"PRIMARY\s+KEY", part, re.I):
                    partition = [tokens[0].lower()]
        order = {}
        om = re.search(r"CLUSTERING\s+ORDER\s+BY\s*\(([^)]*)\)", rest, re.I)
        if om:
            for item in om.group(1).split(","):
                col, *direction = item.split()
                order[col.lower()] = (direction[0] if direction else "ASC").upper()
        tables[name] = {"columns": columns, "partition": partition, "clustering": clustering, "order": order}
    return tables


@pytest.fixture
def schema():
    return parse_cql(ex.read("schema.cql"))


def check_table(t, partition, first_clustering, must_include):
    assert t["partition"] == partition, f"partition key nên là {partition}, đang là {t['partition']}"
    assert t["clustering"], "Thiếu clustering key"
    assert t["clustering"][0] == first_clustering
    for col in must_include:
        assert col in t["clustering"], f"Thêm {col} vào clustering key để hàng là duy nhất"
    assert t["order"].get(first_clustering) == "DESC", f"Cần CLUSTERING ORDER BY ({first_clustering} DESC, ...)"
    for col in t["partition"] + t["clustering"]:
        assert col in t["columns"], f"Cột {col} không có trong bảng"
    assert list(t["order"]) == t["clustering"][: len(t["order"])], "CLUSTERING ORDER BY phải theo thứ tự clustering key"


def test_schema_q1(schema):
    check_table(schema["order_events_by_order"], ["order_id"], "event_time", ["event_type"])


def test_schema_q2(schema):
    check_table(schema["orders_by_seller_day"], ["seller_id", "order_date"], "purchased_at", ["order_id"])


def test_schema_q3(schema):
    check_table(schema["reviews_by_product"], ["product_id"], "created_at", ["review_id"])


# ---------- Biến đổi dữ liệu (offline) ----------

ORDERS = [
    {"order_id": "o1", "purchased_at": datetime(2018, 5, 1, 9, 0),
     "items": [{"seller_id": "s1", "price": 10.0, "freight": 2.0},
               {"seller_id": "s2", "price": 20.5, "freight": 3.0},
               {"seller_id": "s1", "price": 5.25, "freight": 1.0}]},
    {"order_id": "o2", "purchased_at": datetime(2018, 5, 1, 15, 30),
     "items": [{"seller_id": "s1", "price": 99.9, "freight": 10.0}]},
    {"order_id": "o3", "purchased_at": datetime(2018, 5, 2, 8, 0),
     "items": [{"seller_id": "s1", "price": 7.0, "freight": 1.0}]},
]


def test_seller_order_rows():
    load = ex.module("load.py")
    rows = load.seller_order_rows(ORDERS)
    assert rows == [
        {"seller_id": "s1", "order_date": date(2018, 5, 1), "purchased_at": datetime(2018, 5, 1, 9, 0),
         "order_id": "o1", "order_value": 15.25},
        {"seller_id": "s1", "order_date": date(2018, 5, 1), "purchased_at": datetime(2018, 5, 1, 15, 30),
         "order_id": "o2", "order_value": 99.9},
        {"seller_id": "s1", "order_date": date(2018, 5, 2), "purchased_at": datetime(2018, 5, 2, 8, 0),
         "order_id": "o3", "order_value": 7.0},
        {"seller_id": "s2", "order_date": date(2018, 5, 1), "purchased_at": datetime(2018, 5, 1, 9, 0),
         "order_id": "o1", "order_value": 20.5},
    ]


# ---------- Chạy trên Cassandra thật (skip nếu chưa bật) ----------

@pytest.fixture
def session():
    ex.require_service("cassandra")
    from cassandra.cluster import Cluster

    cluster = Cluster(["localhost"], port=9042)
    sess = cluster.connect()
    sess.execute(
        f"CREATE KEYSPACE IF NOT EXISTS {KEYSPACE} "
        "WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}"
    )
    sess.set_keyspace(KEYSPACE)
    for table in ["order_events_by_order", "orders_by_seller_day", "reviews_by_product"]:
        sess.execute(f"DROP TABLE IF EXISTS {table}")
    load = ex.module("load.py")
    for statement in load.split_statements(ex.read("schema.cql")):
        sess.execute(statement)
    yield sess
    cluster.shutdown()


def test_cassandra_roundtrip(session):
    load = ex.module("load.py")
    events = [
        {"order_id": "o1", "event_time": datetime(2018, 5, 1, 9, 0), "event_type": "created", "location": "SP"},
        {"order_id": "o1", "event_time": datetime(2018, 5, 2, 10, 0), "event_type": "shipped", "location": "SP"},
        {"order_id": "o1", "event_time": datetime(2018, 5, 2, 10, 0), "event_type": "invoice", "location": "SP"},
        {"order_id": "o1", "event_time": datetime(2018, 5, 5, 16, 0), "event_type": "delivered", "location": "RJ"},
        {"order_id": "o2", "event_time": datetime(2018, 5, 1, 15, 30), "event_type": "created", "location": "MG"},
    ]
    load.insert_events(session, events)
    history = load.order_history(session, "o1")
    assert [e for _, e in history] == ["delivered", "invoice", "shipped", "created"]
    assert len(load.order_history(session, "o1", limit=2)) == 2

    load.insert_seller_orders(session, load.seller_order_rows(ORDERS))
    assert load.seller_orders(session, "s1", date(2018, 5, 1)) == ["o2", "o1"]
    assert load.seller_orders(session, "s1", date(2018, 5, 2)) == ["o3"]
    assert load.seller_orders(session, "s2", date(2018, 5, 1)) == ["o1"]
