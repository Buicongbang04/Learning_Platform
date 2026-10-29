import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("uplift.ipynb")


def simulate(n: int = 40000, seed: int = 0) -> pd.DataFrame:
    """Thí nghiệm ngẫu nhiên. Email chỉ có tác dụng (+12 điểm %) với khách có x1 > 0."""
    rng = np.random.default_rng(seed)
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    t = rng.binomial(1, 0.5, n)
    true_uplift = 0.12 * (x1 > 0)
    p = 0.10 + 0.05 * (x2 > 0) + true_uplift * t
    return pd.DataFrame({"x1": x1, "x2": x2, "x1_pos": (x1 > 0).astype(float), "treatment": t,
                         "visit": rng.binomial(1, p), "true_uplift": true_uplift})


def test_prepare(nb):
    raw = pd.DataFrame({
        "recency": [1, 2, 3, 4], "history_segment": ["a", "b", "c", "d"], "history": [10.0, 20, 30, 40],
        "mens": [1, 0, 1, 0], "womens": [0, 1, 1, 0], "zip_code": ["Urban", "Rural", "Urban", "Surburban"],
        "newbie": [1, 0, 0, 1], "channel": ["Web", "Phone", "Web", "Web"],
        "segment": ["Womens E-Mail", "No E-Mail", "Mens E-Mail", "No E-Mail"],
        "visit": [1, 0, 1, 0], "conversion": [0, 0, 0, 0], "spend": [0.0, 0, 0, 0],
    })
    out = nb.prepare(raw)
    assert list(out.index) == [0, 1, 3]
    assert list(out.treatment) == [1, 0, 0]
    assert {"zip_code_Urban", "zip_code_Rural", "channel_Web", "channel_Phone"} <= set(out.columns)
    assert "history_segment" not in out.columns and "zip_code" not in out.columns
    assert out["zip_code_Urban"].dtype == float
    assert set(nb.prepare(raw, arm="Mens E-Mail").index) == {1, 2, 3}


def test_qini_small_example(nb):
    uplift = np.array([0.9, 0.5, 0.1, 0.3])
    t = np.array([1, 0, 1, 0])
    y = np.array([1, 0, 0, 1])
    curve = nb.qini_curve(uplift, t, y)
    assert list(curve.columns) == ["frac", "qini"]
    assert curve.frac.to_numpy() == pytest.approx([0.25, 0.5, 0.75, 1.0])
    assert curve.qini.to_numpy() == pytest.approx([1.0, 1.0, 0.5, 0.0])
    assert nb.qini_coefficient(uplift, t, y) == pytest.approx(0.15625)


def test_qini_ties_keep_original_order(nb):
    curve = nb.qini_curve(np.zeros(3), np.array([0, 1, 1]), np.array([1, 1, 0]))
    assert curve.qini.to_numpy() == pytest.approx([0.0, 0.0, -1.0])


@pytest.mark.parametrize("seed", range(3))
def test_qini_rewards_good_ranking(nb, seed):
    df = simulate(seed=seed)
    oracle = nb.qini_coefficient(df.true_uplift.to_numpy() + 1e-9 * df.x2.to_numpy(), df.treatment, df.visit)
    reverse = nb.qini_coefficient(-df.true_uplift.to_numpy(), df.treatment, df.visit)
    noise = nb.qini_coefficient(np.random.default_rng(seed).random(len(df)), df.treatment, df.visit)
    assert oracle > 0.005
    assert reverse < -0.005
    assert abs(noise) < 0.002
    curve = nb.qini_curve(df.true_uplift.to_numpy(), df.treatment, df.visit)
    t = df.treatment == 1
    total = df.visit[t].sum() - df.visit[~t].sum() * t.sum() / (~t).sum()
    assert curve.qini.iloc[-1] == pytest.approx(total)


@pytest.mark.parametrize("seed", range(3))
def test_t_learner_finds_heterogeneity(nb, seed):
    df = simulate(seed=seed)
    train, score = df.iloc[:30000], df.iloc[30000:]
    uplift = nb.t_learner(train, score, ["x1_pos", "x2"], "visit", lambda: LogisticRegression())
    assert uplift.shape == (len(score),)
    pos = score.x1_pos.to_numpy() == 1
    assert uplift[pos].mean() - uplift[~pos].mean() == pytest.approx(0.12, abs=0.03)
    assert nb.qini_coefficient(uplift, score.treatment, score.visit) > 0.004


def test_real_hillstrom(nb):
    raw = pd.read_csv(ex.dataset("hillstrom") / "hillstrom.csv")
    df = nb.prepare(raw)
    assert len(df) == 42693
    t = df.treatment == 1
    assert df.visit[t].mean() - df.visit[~t].mean() == pytest.approx(0.0452, abs=5e-4)
    # khách từng mua hàng nữ phản ứng với email nữ mạnh hơn: xếp hạng theo cột womens có Qini dương
    assert nb.qini_coefficient(df.womens.to_numpy(), df.treatment, df.visit) == pytest.approx(0.0039, abs=2e-4)


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300
