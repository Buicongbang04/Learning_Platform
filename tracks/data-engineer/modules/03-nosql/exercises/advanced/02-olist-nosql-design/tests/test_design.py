import re
from datetime import datetime

import pytest

import testkit
from testkit import Exercise, use_solution

if use_solution():
    pytest.skip("Bài advanced không có lời giải chạy được; xem SOLUTION.md", allow_module_level=True)

ex = Exercise(__file__)

SECTIONS = [
    "Bối cảnh và giả định",
    "Access patterns",
    "Lựa chọn database",
    "Mô hình dữ liệu",
    "Consistency và hỏng hóc",
    "Đưa dữ liệu về lakehouse",
    "Rủi ro và phương án thay thế",
]
LOW_CARDINALITY = {"status", "event_type", "score", "customer_state", "state", "answered"}


# ---------- DESIGN.md ----------

def sections(md: str) -> dict[str, str]:
    parts = re.split(r"^## +(.+?)\s*$", md, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def test_design_doc_complete():
    md = ex.read("DESIGN.md")
    found = sections(md)
    for title in SECTIONS:
        assert title in found, f"Thiếu phần '## {title}'"
        words = len(found[title].split())
        assert words >= 40, f"Phần '{title}' quá ngắn ({words} từ)"
    assert "TODO" not in md, "Còn TODO trong DESIGN.md"
    assert re.search(r"^\|.+\|\s*$\n^\|\s*:?-{3,}", md, flags=re.M), "Cần ít nhất một bảng markdown"
    for word in ["Cassandra", "MongoDB", "QUORUM"]:
        assert word.lower() in md.lower(), f"Tài liệu nên nhắc tới {word}"


# ---------- schema.cql ----------

def _balanced(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
    raise ValueError("Ngoặc không cân bằng")


def _split_top(text):
    parts, depth, cur = [], 0, ""
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def parse_cql(cql):
    text = re.sub(r"(--|//)[^\n]*", "", cql)
    tables = {}
    for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?(\w+)\s*\(", text, re.I):
        body, end = _balanced(text, m.end() - 1)
        semi = text.find(";", end)
        rest = text[end : semi if semi != -1 else len(text)]
        columns, partition, clustering = {}, [], []
        for part in _split_top(body):
            pk = re.match(r"PRIMARY\s+KEY\s*\((.*)\)\s*$", part, re.I | re.S)
            if pk:
                items = _split_top(pk.group(1))
                first = items[0]
                partition = (
                    [c.strip().lower() for c in first.strip("()").split(",")]
                    if first.startswith("(")
                    else [first.lower()]
                )
                clustering = [c.strip().lower() for c in items[1:]]
                continue
            tokens = part.split()
            if len(tokens) >= 2:
                columns[tokens[0].lower()] = " ".join(tokens[1:]).lower()
                if re.search(r"PRIMARY\s+KEY", part, re.I):
                    partition = [tokens[0].lower()]
        order = {}
        om = re.search(r"CLUSTERING\s+ORDER\s+BY\s*\(([^)]*)\)", rest, re.I)
        if om:
            for item in om.group(1).split(","):
                col, *direction = item.split()
                order[col.lower()] = (direction[0] if direction else "ASC").upper()
        tables[m.group(1).lower()] = {
            "columns": columns, "partition": partition, "clustering": clustering, "order": order,
        }
    return tables


@pytest.fixture
def schema():
    return parse_cql(ex.read("schema.cql"))


def test_no_allow_filtering():
    assert "ALLOW FILTERING" not in ex.read("schema.cql").upper()


def test_shipment_events_table(schema):
    t = schema.get("shipment_events_by_order")
    assert t, "Thiếu bảng shipment_events_by_order"
    assert t["partition"] == ["order_id"]
    assert t["clustering"], "Cần clustering key theo thời gian"
    first = t["clustering"][0]
    assert t["columns"][first].startswith(("timestamp", "timeuuid")), "Clustering đầu tiên nên là thời gian"
    assert t["order"].get(first) == "DESC"


def test_late_orders_table(schema):
    t = schema.get("late_orders_by_state_day")
    assert t, "Thiếu bảng late_orders_by_state_day"
    assert any(c in t["partition"] for c in ("customer_state", "state")), "Partition theo bang"
    assert any(t["columns"][c].startswith("date") for c in t["partition"]), "Bucket theo ngày trong partition key"
    assert "order_id" in t["clustering"], "order_id trong clustering để mỗi đơn là một hàng"


def test_partition_keys_not_low_cardinality(schema):
    assert len(schema) >= 2, "Cần ít nhất hai bảng"
    for name, t in schema.items():
        assert t["partition"], f"Bảng {name} thiếu PRIMARY KEY"
        assert not set(t["partition"]) <= LOW_CARDINALITY, f"Partition key của {name} có cardinality quá thấp"
        for col in t["partition"] + t["clustering"]:
            assert col in t["columns"], f"{name}: cột {col} chưa khai báo"


# ---------- mongo_schema.py ----------

def _types(prop):
    t = prop.get("bsonType", prop.get("type"))
    return {t} if isinstance(t, str) else set(t or [])


def test_review_validator():
    mod = ex.module("mongo_schema.py")
    schema = mod.REVIEW_VALIDATOR.get("$jsonSchema")
    assert schema, "REVIEW_VALIDATOR phải có khoá $jsonSchema"
    required = set(schema.get("required", []))
    assert {"_id", "order_id", "product_id", "score", "created_at"} <= required
    props = schema["properties"]
    assert _types(props["score"]) & {"int", "number"}
    assert props["score"].get("minimum") == 1 and props["score"].get("maximum") == 5
    assert "date" in _types(props["created_at"])


def test_review_indexes():
    mod = ex.module("mongo_schema.py")
    idx = [[(f, d) for f, d in index] for index in mod.REVIEW_INDEXES]
    assert any(i[:2] == [("product_id", 1), ("created_at", -1)] for i in idx), "Index cho review mới nhất theo sản phẩm"
    assert any(i[0][0] == "order_id" for i in idx), "Index tra review theo order_id"
    assert any({"score", "created_at"} <= {f for f, _ in i} for i in idx), "Index cho hàng đợi review điểm thấp"


# ---------- Dịch vụ thật ----------

def test_cassandra_schema_applies():
    ex.require_service("cassandra")
    from cassandra.cluster import Cluster

    cluster = Cluster(["localhost"], port=9042)
    session = cluster.connect()
    session.execute(
        "CREATE KEYSPACE IF NOT EXISTS de_ex03_design "
        "WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}"
    )
    session.set_keyspace("de_ex03_design")
    text = re.sub(r"(--|//)[^\n]*", "", ex.read("schema.cql"))
    for name in parse_cql(text):
        session.execute(f"DROP TABLE IF EXISTS {name}")
    for statement in [s.strip() for s in text.split(";") if s.strip()]:
        session.execute(statement)
    cluster.shutdown()


def test_mongo_validator_rejects_bad_review():
    ex.require_service("mongo")
    import pymongo
    from pymongo.errors import WriteError

    mod = ex.module("mongo_schema.py")
    client = pymongo.MongoClient(testkit.MONGO_URI, serverSelectionTimeoutMS=2000)
    client.drop_database("ex03_design")
    db = client.ex03_design
    db.create_collection("reviews", validator=mod.REVIEW_VALIDATOR)
    for index in mod.REVIEW_INDEXES:
        db.reviews.create_index(index)
    good = {"_id": "r1", "order_id": "o1", "product_id": "p1", "score": 4, "created_at": datetime(2018, 5, 1)}
    db.reviews.insert_one(good)
    with pytest.raises(WriteError):
        db.reviews.insert_one({**good, "_id": "r2", "score": 7})
    with pytest.raises(WriteError):
        db.reviews.insert_one({"_id": "r3", "order_id": "o3", "score": 3, "created_at": datetime(2018, 5, 1)})
    client.drop_database("ex03_design")
    client.close()
