import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def charts():
    return ex.module("charts.py")


def spec(chart, sort, zero):
    return {"chart": chart, "sort": sort, "zero_baseline": zero}


def test_trend(charts):
    assert charts.choose_chart("trend") == spec("line", "natural", False)
    assert charts.choose_chart("trend", n_categories=5) == spec("line", "natural", False)
    assert charts.choose_chart("trend", n_categories=12)["chart"] == "small_multiples"


def test_comparison_nominal_sorted_descending(charts):
    assert charts.choose_chart("comparison", n_categories=5) == spec("bar", "descending", True)
    assert charts.choose_chart("comparison", n_categories=27) == spec("barh", "descending", True)


def test_comparison_ordered_keeps_natural_order(charts):
    assert charts.choose_chart("comparison", n_categories=5, ordered=True) == spec("bar", "natural", True)
    assert charts.choose_chart("comparison", n_categories=24, ordered=True)["sort"] == "natural"


def test_distribution(charts):
    assert charts.choose_chart("distribution", n_points=95824) == spec("histogram", None, True)
    assert charts.choose_chart("distribution", n_points=None) == spec("histogram", None, True)
    assert charts.choose_chart("distribution", n_categories=3, n_points=5000) == spec("box", None, False)
    assert charts.choose_chart("distribution", n_points=12) == spec("strip", None, False)
    assert charts.choose_chart("distribution", n_categories=3, n_points=20)["chart"] == "strip"


def test_relationship(charts):
    assert charts.choose_chart("relationship", n_points=800) == spec("scatter", None, False)
    assert charts.choose_chart("relationship", n_points=5000)["chart"] == "scatter"
    assert charts.choose_chart("relationship", n_points=95824) == spec("hexbin", None, False)


def test_composition_never_pie(charts):
    assert charts.choose_chart("composition", n_categories=3) == spec("stacked_bar_100", None, True)
    assert charts.choose_chart("composition", n_categories=8) == spec("barh", "descending", True)
    for k in range(1, 20):
        assert charts.choose_chart("composition", n_categories=k)["chart"] != "pie"


def test_bars_always_start_at_zero(charts):
    for goal, kw in [("comparison", {"n_categories": 3}), ("comparison", {"n_categories": 30}),
                     ("composition", {"n_categories": 4}), ("composition", {"n_categories": 9})]:
        out = charts.choose_chart(goal, **kw)
        assert "bar" in out["chart"] and out["zero_baseline"] is True


def test_invalid_goal(charts):
    with pytest.raises(ValueError):
        charts.choose_chart("pie")


def test_top_n_with_other(charts):
    s = pd.Series({"a": 5, "b": 40, "c": 10, "d": 3, "e": 20}, name="orders")
    out = charts.top_n_with_other(s, 3)
    assert list(out.index) == ["b", "e", "c", "Khác"]
    assert out.tolist() == [40, 20, 10, 8]
    assert out.sum() == s.sum()
    assert out.name == "orders"


def test_top_n_other_stays_last_even_if_largest(charts):
    s = pd.Series({f"c{i}": 10 - i for i in range(10)})
    out = charts.top_n_with_other(s, 2, other_label="other")
    assert list(out.index) == ["c0", "c1", "other"]
    assert out["other"] == sum(10 - i for i in range(2, 10))


def test_top_n_without_rest(charts):
    s = pd.Series({"a": 1, "b": 2})
    out = charts.top_n_with_other(s, 5)
    assert list(out.index) == ["b", "a"]


def test_category_share_counts_missing(charts):
    df = pd.DataFrame({"cat": ["x", "x", "x", None, None, "y", "z", "w"]})
    out = charts.category_share(df, "cat", 2)
    assert list(out.index) == ["x", "(thiếu)", "Khác"]
    assert out["count"].tolist() == [3, 2, 3]
    assert out["share"].sum() == pytest.approx(1.0)
    assert out.loc["x", "share"] == pytest.approx(3 / 8)
    assert list(out.columns) == ["count", "share"]


def test_real_olist_product_categories(charts):
    path = ROOT / "data" / "raw" / "olist_products_dataset.csv"
    if not path.exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    products = pd.read_csv(path)
    out = charts.category_share(products, "product_category_name", 5)
    assert out.index[0] == "cama_mesa_banho" and out["count"].iloc[0] == 3029
    assert out.index[-1] == "Khác" and out["count"].iloc[-1] == 19619
    assert out["count"].sum() == 32951
    full = charts.category_share(products, "product_category_name", 100)
    assert full.loc["(thiếu)", "count"] == 610
