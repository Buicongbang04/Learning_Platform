import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("ratio_aa.ipynb")


def make_items(n_customers: int, seed: int) -> pd.DataFrame:
    """Mỗi khách mua nhiều món cùng mức giá (gom cụm mạnh), như mua 5 cái ốp lưng giống nhau."""
    rng = np.random.default_rng(seed)
    n_items = 1 + rng.poisson(3, n_customers)
    level = rng.lognormal(4.5, 0.8, n_customers)
    cust = np.repeat(np.arange(n_customers), n_items)
    price = level[cust] * rng.lognormal(0, 0.05, len(cust))
    return pd.DataFrame({"customer_unique_id": [f"c{i:05d}" for i in cust], "price": price})


def test_hash_assign_is_deterministic_and_salted(nb):
    ids = np.array([f"c{i}" for i in range(20000)])
    a = nb.hash_assign(ids, "exp-1")
    assert a.dtype == bool and a.shape == (20000,)
    assert np.array_equal(a, nb.hash_assign(ids, "exp-1"))
    assert 0.48 < a.mean() < 0.52
    b = nb.hash_assign(ids, "exp-2")
    assert 0.45 < (a == b).mean() < 0.55          # salt khác → phân nhóm độc lập
    assert 0.08 < nb.hash_assign(ids, "exp-1", share=0.1).mean() < 0.12
    # cùng khách ở bất kỳ vị trí nào cũng cùng nhóm
    assert nb.hash_assign(ids[::-1], "exp-1")[::-1].tolist() == a.tolist()


def test_customer_table(nb):
    items = pd.DataFrame({"customer_unique_id": ["a", "b", "a", "c", "a"], "price": [10.0, 5, 30, 7, 20]})
    table = nb.customer_table(items)
    assert table.loc["a", "revenue"] == 60 and table.loc["a", "n_items"] == 3
    assert table.loc["b", "revenue"] == 5 and table.loc["c", "n_items"] == 1
    assert len(table) == 3


def test_delta_test_values(nb):
    items = make_items(3000, seed=1)
    table = nb.customer_table(items)
    treat = np.random.default_rng(0).random(len(table)) < 0.5
    out = nb.delta_test(table, treat)
    a, b = table[~treat], table[treat]
    assert out["ratio_a"] == pytest.approx(a.revenue.sum() / a.n_items.sum())
    assert out["diff"] == pytest.approx(out["ratio_b"] - out["ratio_a"])
    assert 0 <= out["p_value"] <= 1 and out["se"] > 0


def test_naive_test_is_item_level_welch(nb):
    rng = np.random.default_rng(2)
    pa, pb = rng.normal(100, 20, 500), rng.normal(103, 20, 400)
    out = nb.naive_test(pa, pb)
    assert out["diff"] == pytest.approx(pb.mean() - pa.mean())
    assert out["se"] == pytest.approx(np.sqrt(pa.var(ddof=1) / 500 + pb.var(ddof=1) / 400))


def test_aa_study_shows_naive_false_alarms(nb):
    items = make_items(2000, seed=3)
    rates = nb.aa_study(items, n_sims=300, seed=0)
    assert 0.015 <= rates["delta"] <= 0.095
    assert rates["naive"] > 0.2


def test_aa_study_reproducible(nb):
    items = make_items(500, seed=4)
    assert nb.aa_study(items, n_sims=30, seed=5) == nb.aa_study(items, n_sims=30, seed=5)


def test_real_olist():
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    nb = ex.notebook("ratio_aa.ipynb")
    items = nb.load_items(raw)
    table = nb.customer_table(items)
    assert len(table) == pytest.approx(93350, abs=50)
    assert table.revenue.sum() / table.n_items.sum() == pytest.approx(119.98, abs=0.05)
    treat = nb.hash_assign(table.index.to_numpy(), "olist-aov-aa")
    out = nb.delta_test(table, treat)
    in_b = items.customer_unique_id.isin(table.index[treat])
    naive = nb.naive_test(items.price[~in_b].to_numpy(), items.price[in_b].to_numpy())
    design_effect = (out["se"] / naive["se"]) ** 2
    assert 1.05 < design_effect < 1.35
