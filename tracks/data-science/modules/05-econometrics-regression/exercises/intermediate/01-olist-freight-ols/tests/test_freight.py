import numpy as np
import pandas as pd
import pytest
import statsmodels.formula.api as smf

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("freight.ipynb")


def test_haversine_known_distances(nb):
    # 1 độ kinh tuyến ở xích đạo = 2*pi*6371/360 km
    assert nb.haversine_km(0, 0, 0, 1) == pytest.approx(2 * np.pi * 6371 / 360, rel=1e-9)
    assert nb.haversine_km(-23.55, -46.63, -23.55, -46.63) == pytest.approx(0, abs=1e-9)
    sp_rj = nb.haversine_km(-23.55, -46.63, -22.91, -43.17)       # São Paulo - Rio de Janeiro
    assert 355 < sp_rj < 365
    assert nb.haversine_km(-22.91, -43.17, -23.55, -46.63) == pytest.approx(sp_rj)
    out = nb.haversine_km(np.zeros(3), np.zeros(3), np.zeros(3), np.array([1.0, 2.0, 3.0]))
    assert np.asarray(out) == pytest.approx(2 * np.pi * 6371 / 360 * np.array([1, 2, 3]), rel=1e-9)


def fixture_tables():
    orders = pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4", "o5", "o6", "o7", "o8", "o9"],
        "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9"],
        "order_status": ["delivered", "delivered", "canceled", "delivered", "delivered", "delivered",
                         "delivered", "delivered", "delivered"],
        "order_delivered_customer_date": pd.to_datetime([
            "2018-01-05", "2018-01-05", None, None, "2018-01-05", "2018-01-05", "2018-01-05", "2018-01-05",
            "2018-01-05"]),
    })
    items = pd.DataFrame({
        "order_id": ["o1", "o2", "o2", "o3", "o4", "o5", "o6", "o7", "o8", "o9"],
        "order_item_id": [1, 1, 2, 1, 1, 1, 1, 1, 1, 1],
        "product_id": ["p1", "p1", "p2", "p1", "p1", "p1", "p1", "p3", "p1", "p2"],
        "seller_id": ["sA", "sA", "sA", "sA", "sA", "sX", "sA", "sA", "sA", "sB"],
        "price": [100.0, 50.0, 50.0, 80.0, 80.0, 80.0, 80.0, 80.0, 80.0, 40.0],
        "freight_value": [20.0, 10.0, 10.0, 15.0, 15.0, 15.0, 0.0, 15.0, 15.0, 8.0],
    })
    customers = pd.DataFrame({
        "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9"],
        "customer_zip_code_prefix": ["20000", "20000", "20000", "20000", "20000", "20000", "20000", "01000", "01500"],
        "customer_state": ["RJ", "RJ", "RJ", "RJ", "RJ", "RJ", "RJ", "SP", "SP"],
    })
    sellers = pd.DataFrame({
        "seller_id": ["sA", "sB", "sX"],
        "seller_zip_code_prefix": ["01000", "01000", "99999"],   # 99999 không có trong geolocation
        "seller_state": ["SP", "SP", "SP"],
    })
    products = pd.DataFrame({
        "product_id": ["p1", "p2", "p3"],
        "product_weight_g": [500.0, 1000.0, np.nan],
        "product_length_cm": [20.0, 10.0, 10.0],
        "product_height_cm": [10.0, 10.0, 10.0],
        "product_width_cm": [15.0, 10.0, 10.0],
    })
    geo = pd.DataFrame({   # nhiều toạ độ mỗi prefix: dùng trung vị
        "geolocation_zip_code_prefix": ["01000", "01000", "01000", "20000", "20000", "01500"],
        "geolocation_lat": [-23.55, -23.50, -30.00, -22.90, -22.92, -23.60],
        "geolocation_lng": [-46.63, -46.60, -50.00, -43.17, -43.17, -46.70],
    })
    return items, orders, customers, sellers, products, geo


def test_build_table_filters(nb):
    d = nb.build_freight_table(*fixture_tables())
    # o2: 2 món; o3: huỷ; o4: chưa có ngày giao; o5: seller thiếu toạ độ; o6: freight 0;
    # o7: thiếu cân nặng; o8: cùng zip prefix (khoảng cách 0) -> còn o1, o9
    assert sorted(d.order_id) == ["o1", "o9"]


def test_build_table_values(nb):
    d = nb.build_freight_table(*fixture_tables()).set_index("order_id")
    expected = nb.haversine_km(-22.91, -43.17, -23.55, -46.63)   # trung vị của 20000 và 01000
    assert d.loc["o1", "distance_km"] == pytest.approx(expected, rel=1e-9)
    assert d.loc["o1", "same_state"] == 0 and d.loc["o9", "same_state"] == 1
    assert d.loc["o1", "volume_cm3"] == pytest.approx(3000)
    assert d.loc["o1", "log_freight"] == pytest.approx(np.log(20))
    assert d.loc["o1", "log_weight"] == pytest.approx(np.log(500))
    assert d.loc["o1", "log_volume"] == pytest.approx(np.log(3000))
    assert d.loc["o1", "log_distance"] == pytest.approx(np.log1p(expected))
    assert d.loc["o9", "log_price"] == pytest.approx(np.log(40))
    assert d.loc["o9", "seller_id"] == "sB"


def simulate(seed: int, n_sellers: int = 200, per_seller: int = 30) -> pd.DataFrame:
    """Đơn của cùng seller có cân nặng giống nhau và chung một cú sốc phí ship."""
    rng = np.random.default_rng(seed)
    seller = np.repeat(np.arange(n_sellers), per_seller)
    n = len(seller)
    log_weight = rng.normal(6.5, 1, n_sellers)[seller] + rng.normal(0, 0.3, n)
    log_volume = 0.8 * log_weight + rng.normal(3, 0.4, n)
    log_distance = rng.normal(6, 1, n)
    same_state = (rng.random(n) < 0.3).astype(int)
    log_price = 0.5 * log_weight + rng.normal(1.5, 0.6, n)
    log_freight = (0.5 + 0.13 * log_weight + 0.03 * log_volume + 0.14 * log_distance - 0.22 * same_state
                   + 0.1 * log_price + rng.normal(0, 0.3, n_sellers)[seller] + rng.normal(0, 0.2, n))
    return pd.DataFrame({"seller_id": [f"s{i}" for i in seller], "log_freight": log_freight,
                         "log_weight": log_weight, "log_volume": log_volume, "log_distance": log_distance,
                         "same_state": same_state, "log_price": log_price})


def test_formula_and_fit(nb):
    df = simulate(0)
    res = nb.fit_freight(df)
    ref = smf.ols(nb.FORMULA, df).fit()
    assert list(res.params.index) == ["Intercept", "log_weight", "log_volume", "log_distance", "same_state", "log_price"]
    assert res.params.to_numpy() == pytest.approx(ref.params.to_numpy())
    assert res.params["log_distance"] == pytest.approx(0.14, abs=0.02)


def test_cov_types(nb):
    df = simulate(1)
    hc3 = smf.ols(nb.FORMULA, df).fit(cov_type="HC3").bse
    cl = smf.ols(nb.FORMULA, df).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df.seller_id)[0]}).bse
    assert nb.fit_freight(df, "HC3").bse.to_numpy() == pytest.approx(hc3.to_numpy())
    assert nb.fit_freight(df, "cluster").bse.to_numpy() == pytest.approx(cl.to_numpy())


@pytest.mark.parametrize("seed", [2, 3])
def test_compare_se_cluster_larger_for_seller_level_variable(nb, seed):
    se = nb.compare_se(simulate(seed))
    assert list(se.columns) == ["classic", "HC3", "cluster"]
    assert se.loc["log_weight", "cluster"] > 1.5 * se.loc["log_weight", "classic"]
    assert se.loc["log_distance", "cluster"] < 1.3 * se.loc["log_distance", "classic"]


def test_effects(nb):
    class Fake:
        params = pd.Series({"log_distance": 0.15, "same_state": -0.2, "log_weight": 0.1})
    out = nb.effects(Fake())
    assert out["distance_doubling"] == pytest.approx(2**0.15 - 1)
    assert out["same_state"] == pytest.approx(np.exp(-0.2) - 1)
    assert out["weight_10pct"] == pytest.approx(1.1**0.1 - 1)


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_geolocation_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    d = nb.build_freight_table(
        pd.read_csv(raw / "olist_order_items_dataset.csv"),
        pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=["order_delivered_customer_date"]),
        pd.read_csv(raw / "olist_customers_dataset.csv", dtype={"customer_zip_code_prefix": str}),
        pd.read_csv(raw / "olist_sellers_dataset.csv", dtype={"seller_zip_code_prefix": str}),
        pd.read_csv(raw / "olist_products_dataset.csv"),
        pd.read_csv(raw / "olist_geolocation_dataset.csv", dtype={"geolocation_zip_code_prefix": str}),
    )
    assert len(d) == 86065
    res = nb.fit_freight(d)
    assert res.rsquared == pytest.approx(0.655, abs=1e-3)
    assert res.params["log_distance"] == pytest.approx(0.1418, abs=1e-3)
    assert res.params["same_state"] == pytest.approx(-0.2242, abs=1e-3)
