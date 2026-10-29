import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

FEATURES = ["recency", "history", "mens", "womens", "newbie", "channel", "zip_code"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("variance_reduction.ipynb")


def make_df(n: int = 6000, seed: int = 0, lift: float = 0.05) -> pd.DataFrame:
    """Giống cấu trúc Hillstrom: visit phụ thuộc mạnh vào history và channel, email nữ tăng visit."""
    rng = np.random.default_rng(seed)
    history = rng.lognormal(5, 0.8, n)
    channel = rng.choice(["Web", "Phone", "Multichannel"], n)
    segment = rng.choice(["No E-Mail", "Womens E-Mail", "Mens E-Mail"], n)
    logit = -2.5 + 0.9 * (np.log(history) - 5) / 0.8 + 0.8 * (channel == "Web")
    p = 1 / (1 + np.exp(-logit)) + lift * (segment == "Womens E-Mail")
    visit = (rng.random(n) < p).astype(int)
    return pd.DataFrame({
        "recency": rng.integers(1, 13, n), "history": history, "mens": rng.integers(0, 2, n),
        "womens": rng.integers(0, 2, n), "newbie": rng.integers(0, 2, n), "channel": channel,
        "zip_code": rng.choice(["Urban", "Rural", "Surburban"], n), "segment": segment,
        "visit": visit, "spend": visit * rng.exponential(20, n),
    })


def test_cuped_effect_keys_and_raw(nb):
    df = make_df()
    out = nb.cuped_effect(df, "visit", "history", "Womens E-Mail")
    assert {"diff", "se", "diff_raw", "se_raw", "theta", "var_reduction"} <= set(out)
    a = df[df.segment == "No E-Mail"].visit
    b = df[df.segment == "Womens E-Mail"].visit
    assert out["diff_raw"] == pytest.approx(b.mean() - a.mean())
    assert out["se_raw"] == pytest.approx(np.sqrt(a.var() / len(a) + b.var() / len(b)))


def test_cuped_effect_uses_only_two_arms(nb):
    df = make_df(seed=1)
    out = nb.cuped_effect(df, "visit", "history", "Womens E-Mail")
    two = df[df.segment.isin(["No E-Mail", "Womens E-Mail"])]
    theta = np.cov(two.visit, two.history)[0, 1] / two.history.var()
    assert out["theta"] == pytest.approx(theta)
    assert out["se"] < out["se_raw"]
    assert 0 < out["var_reduction"] < 1


def test_cuped_effect_custom_control(nb):
    df = make_df(seed=2)
    out = nb.cuped_effect(df, "visit", "history", "Womens E-Mail", control="Mens E-Mail")
    a = df[df.segment == "Mens E-Mail"].visit
    b = df[df.segment == "Womens E-Mail"].visit
    assert out["diff_raw"] == pytest.approx(b.mean() - a.mean())


def test_regression_without_covariates_is_plain_difference(nb):
    df = make_df(seed=3)
    diff, se = nb.regression_effect(df, "visit", [], "Womens E-Mail")
    out = nb.cuped_effect(df, "visit", "history", "Womens E-Mail")
    assert diff == pytest.approx(out["diff_raw"])
    assert se == pytest.approx(out["se_raw"], rel=0.01)


def test_regression_with_one_covariate_is_close_to_cuped(nb):
    df = make_df(seed=4)
    diff, se = nb.regression_effect(df, "visit", ["history"], "Womens E-Mail")
    out = nb.cuped_effect(df, "visit", "history", "Womens E-Mail")
    assert abs(diff - out["diff"]) < 0.1 * out["se"]
    assert se == pytest.approx(out["se"], rel=0.03)


def test_regression_handles_categorical_covariates(nb):
    df = make_df(seed=5)
    _, se_num = nb.regression_effect(df, "visit", ["history"], "Womens E-Mail")
    diff, se = nb.regression_effect(df, "visit", ["history", "channel", "zip_code"], "Womens E-Mail")
    assert se < se_num            # channel giải thích thêm variance
    assert diff == pytest.approx(0.05, abs=0.04)


def test_cupac_is_out_of_fold(nb):
    df = make_df(n=3000, seed=6)
    pred = nb.cupac_covariate(df, FEATURES, "visit")
    assert pred.shape == (len(df),)
    leaked = df.copy()
    leaked.loc[0, "visit"] = 1000   # đổi outcome của chính dòng 0
    pred2 = nb.cupac_covariate(leaked, FEATURES, "visit")
    assert pred2[0] == pytest.approx(pred[0])   # dự đoán dòng 0 không được thấy outcome của nó


def test_cupac_predicts_better_than_single_covariate(nb):
    df = make_df(n=8000, seed=7)
    pred = nb.cupac_covariate(df, FEATURES, "visit")
    rho2_cupac = np.corrcoef(df.visit, pred)[0, 1] ** 2
    rho2_history = np.corrcoef(df.visit, df.history)[0, 1] ** 2
    assert rho2_cupac > rho2_history
    df["cupac"] = pred
    out = nb.cuped_effect(df, "visit", "cupac", "Womens E-Mail")
    assert out["var_reduction"] == pytest.approx(rho2_cupac, abs=0.03)


def test_real_hillstrom(nb):
    df = pd.read_csv(ex.dataset("hillstrom") / "hillstrom.csv")
    out = nb.cuped_effect(df, "visit", "history", "Womens E-Mail")
    assert out["diff_raw"] == pytest.approx(0.0452, abs=5e-4)
    assert out["var_reduction"] < 0.01          # history là covariate yếu cho visit
    diff, se = nb.regression_effect(df, "visit", FEATURES, "Womens E-Mail")
    assert diff == pytest.approx(0.0454, abs=1e-3)
    assert se < 0.995 * out["se_raw"]
    pred = nb.cupac_covariate(df, FEATURES, "visit")
    assert np.corrcoef(df.visit, pred)[0, 1] ** 2 > 0.015
