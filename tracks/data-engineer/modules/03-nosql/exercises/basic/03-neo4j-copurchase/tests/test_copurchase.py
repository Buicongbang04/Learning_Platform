import re

import pytest

import testkit
from testkit import Exercise

ex = Exercise(__file__)

PREFIX = "ex03b03_"


def purchases():
    raw = [
        ("c1", "o1", "p1", "housewares"),
        ("c1", "o1", "p2", "bed_bath_table"),
        ("c1", "o9", "p2", "bed_bath_table"),  # mua p2 hai lần, vẫn chỉ tính 1 khách
        ("c2", "o2", "p1", "housewares"),
        ("c2", "o2", "p3", "housewares"),
        ("c2", "o3", "p2", "bed_bath_table"),
        ("c3", "o4", "p1", "housewares"),
        ("c3", "o4", "p4", "toys"),
        ("c4", "o5", "p3", "housewares"),
        ("c4", "o5", "p5", "toys"),
        ("c5", "o6", "p5", "toys"),
    ]
    return [
        {"customer_id": PREFIX + c, "order_id": PREFIX + o, "product_id": PREFIX + p, "category": cat}
        for c, o, p, cat in raw
    ]


def p(name):
    return PREFIX + name


@pytest.fixture
def graph():
    return ex.module("graph.py")


def test_co_purchase_python(graph):
    result = graph.co_purchase_counts(purchases(), p("p1"))
    assert result == [(p("p2"), 2), (p("p3"), 1), (p("p4"), 1)]
    assert graph.co_purchase_counts(purchases(), p("p1"), k=1) == [(p("p2"), 2)]
    assert graph.co_purchase_counts(purchases(), p("p5")) == [(p("p3"), 1)]
    assert graph.co_purchase_counts(purchases(), "unknown") == []


def test_cypher_static(graph):
    load = graph.LOAD_QUERY.upper()
    assert "UNWIND $ROWS" in re.sub(r"\s+", " ", load)
    assert load.count("MERGE") >= 3
    without_on_create = re.sub(r"\bON\s+CREATE\b", "", load)
    assert not re.search(r"\bCREATE\b", without_on_create), "Dùng MERGE để nạp idempotent"
    q = graph.COPURCHASE_QUERY
    assert "$pid" in q and "$k" in q
    assert ":BOUGHT" in q.upper()
    assert len(graph.CONSTRAINTS) == 2
    for c in graph.CONSTRAINTS:
        assert "IF NOT EXISTS" in c.upper() and "UNIQUE" in c.upper()


@pytest.fixture
def driver():
    ex.require_service("neo4j")
    from neo4j import GraphDatabase

    drv = GraphDatabase.driver(testkit.NEO4J_URI, auth=testkit.NEO4J_AUTH)
    cleanup = "MATCH (n) WHERE n.id STARTS WITH $prefix DETACH DELETE n"
    drv.execute_query(cleanup, prefix=PREFIX)
    yield drv
    drv.execute_query(cleanup, prefix=PREFIX)
    drv.close()


def test_neo4j_load_and_query(graph, driver):
    graph.load_purchases(driver, purchases())
    graph.load_purchases(driver, purchases())  # idempotent
    records, _, _ = driver.execute_query(
        "MATCH (c:Customer) WHERE c.id STARTS WITH $prefix RETURN count(c) AS n", prefix=PREFIX
    )
    assert records[0]["n"] == 5
    records, _, _ = driver.execute_query(
        "MATCH (:Customer)-[b:BOUGHT]->(p:Product) WHERE p.id STARTS WITH $prefix RETURN count(b) AS n",
        prefix=PREFIX,
    )
    assert records[0]["n"] == 11
    for pid in ["p1", "p3", "p5"]:
        assert graph.co_purchase(driver, p(pid)) == graph.co_purchase_counts(purchases(), p(pid))
