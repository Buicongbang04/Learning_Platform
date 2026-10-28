import pytest

from testkit import Exercise

ex = Exercise(__file__)

EXPECTED = {
    "staging.orders": {"raw.orders"},
    "staging.customers": {"raw.customers"},
    "staging.order_items": set(),
    "mart.fct_orders": {"staging.order_items", "staging.orders"},
    "mart.dim_customers": {"staging.customers", "staging.orders"},
    "reporting.revenue_by_state": {"mart.fct_orders", "mart.dim_customers"},
}


@pytest.fixture(scope="module")
def lin():
    return ex.module("lineage.py")


def fixture_graph(lin):
    script = (ex.fixtures / "pipeline.sql").read_text(encoding="utf-8")
    return lin.build_graph(lin.split_statements(script))


def test_parse_simple(lin):
    assert lin.parse_statement("CREATE TABLE a.b AS SELECT * FROM c.d JOIN e ON 1=1") == ("a.b", {"c.d", "e"})
    assert lin.parse_statement("insert into T1 (x, y) select x, y from T2 left outer join T3 using (x)") == (
        "t1", {"t2", "t3"})
    assert lin.parse_statement("SELECT * FROM a") is None
    assert lin.parse_statement("INSERT INTO t SELECT * FROM t WHERE false") == ("t", set())


def test_parse_cte_excluded(lin):
    sql = """CREATE VIEW v AS WITH x AS (SELECT * FROM s1), y AS (SELECT * FROM x JOIN s2 USING (k))
             SELECT * FROM y"""
    assert lin.parse_statement(sql) == ("v", {"s1", "s2"})


def test_graph_from_fixture(lin):
    graph = fixture_graph(lin)
    assert graph == EXPECTED


def test_upstream_downstream(lin):
    graph = fixture_graph(lin)
    assert lin.upstream(graph, "reporting.revenue_by_state") == {
        "mart.fct_orders", "mart.dim_customers", "staging.order_items", "staging.orders",
        "staging.customers", "raw.orders", "raw.customers"}
    assert lin.upstream(graph, "raw.orders") == set()
    assert lin.downstream(graph, "raw.orders") == {
        "staging.orders", "mart.fct_orders", "mart.dim_customers", "reporting.revenue_by_state"}
    assert lin.downstream(graph, "raw.customers") == {
        "staging.customers", "mart.dim_customers", "reporting.revenue_by_state"}
    assert lin.downstream(graph, "reporting.revenue_by_state") == set()


def test_run_order(lin):
    graph = fixture_graph(lin)
    assert lin.run_order(graph) == [
        "staging.customers", "staging.order_items", "staging.orders",
        "mart.dim_customers", "mart.fct_orders", "reporting.revenue_by_state"]


def test_cycle(lin):
    g = lin.build_graph(["CREATE TABLE a AS SELECT * FROM b", "CREATE TABLE b AS SELECT * FROM a"])
    with pytest.raises(ValueError):
        lin.run_order(g)


def test_merge_multiple_writers(lin):
    g = lin.build_graph(["INSERT INTO m SELECT * FROM a", "INSERT INTO m SELECT * FROM b", "SELECT 1"])
    assert g == {"m": {"a", "b"}}
