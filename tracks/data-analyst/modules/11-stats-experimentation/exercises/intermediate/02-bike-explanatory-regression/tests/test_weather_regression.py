import numpy as np
import pandas as pd
import pytest
import statsmodels.formula.api as smf

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("weather_regression.ipynb")


def raw_fixture():
    return pd.DataFrame({
        "temp": [0.2, 0.5], "hum": [0.5, 0.8], "windspeed": [0.1, 0.3],
        "season": [1, 4], "weathersit": [1, 3], "yr": [0, 1], "cnt": [100, 200],
    })


def test_prepare(nb):
    raw = raw_fixture()
    before = raw.copy()
    out = nb.prepare(raw)
    assert out["temp_c"].tolist() == pytest.approx([8.2, 20.5])
    assert out["hum_pct"].tolist() == pytest.approx([50.0, 80.0])
    assert out["wind_kmh"].tolist() == pytest.approx([6.7, 20.1])
    assert out["season_name"].tolist() == ["spring", "winter"]
    assert out["weather"].tolist() == ["clear", "light_rain_snow"]
    assert out["year"].tolist() == [2011, 2012]
    pd.testing.assert_frame_equal(raw, before)


def synthetic():
    rng = np.random.default_rng(11)
    n = 300
    x = rng.uniform(0, 30, n)
    z = rng.integers(0, 2, n)
    y = 50 + 10 * x - 0.2 * x**2 + 40 * z + rng.normal(0, 5 + x / 3, n)  # phương sai sai số tăng theo x
    return pd.DataFrame({"x": x, "z": z, "y": y})


def test_fit_explanatory_hc3_and_hac(nb):
    df = synthetic()
    res = nb.fit_explanatory(df, "y ~ x + z")
    ref = smf.ols("y ~ x + z", df).fit(cov_type="HC3")
    assert res.cov_type == "HC3"
    assert res.params["x"] == pytest.approx(ref.params["x"])
    assert res.bse["x"] == pytest.approx(ref.bse["x"])
    hac = nb.fit_explanatory(df, "y ~ x + z", cov_type="HAC")
    ref_hac = smf.ols("y ~ x + z", df).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
    assert hac.bse["x"] == pytest.approx(ref_hac.bse["x"])


def test_effect_table(nb):
    df = synthetic()
    res = smf.ols("y ~ x + z", df).fit(cov_type="HC3")
    out = nb.effect_table(res, {"z": 1, "x": 5})
    assert list(out.index) == ["z", "x"]
    assert list(out.columns) == ["unit", "effect", "ci_low", "ci_high", "p"]
    ci = res.conf_int()
    assert out.loc["x", "effect"] == pytest.approx(res.params["x"] * 5)
    assert out.loc["x", "ci_low"] == pytest.approx(ci.loc["x", 0] * 5)
    assert out.loc["z", "ci_high"] == pytest.approx(ci.loc["z", 1])
    assert out.loc["z", "p"] == pytest.approx(res.pvalues["z"])


def test_coef_path(nb):
    df = synthetic()
    out = nb.coef_path(df, "x", {"một biến": "y ~ x", "thêm z": "y ~ x + z"})
    assert out.name == "x"
    assert list(out.index) == ["một biến", "thêm z"]
    assert out["thêm z"] == pytest.approx(smf.ols("y ~ x + z", df).fit().params["x"])


def test_turning_point(nb):
    df = synthetic()
    res = smf.ols("y ~ x + I(x ** 2) + z", df).fit()
    peak = nb.turning_point(res, "x", "I(x ** 2)")
    assert peak == pytest.approx(-res.params["x"] / (2 * res.params["I(x ** 2)"]))
    assert 20 < peak < 30  # đường thật: 10 / (2 * 0.2) = 25


@pytest.fixture(scope="module")
def real_raw():
    return pd.read_csv(ex.dataset("bike-sharing-uci") / "day.csv", parse_dates=["dteday"])


def test_real_model(nb, real_raw):
    day = nb.prepare(real_raw)
    res = nb.fit_explanatory(day)
    assert int(res.nobs) == 731
    assert res.rsquared == pytest.approx(0.8228, abs=1e-3)
    assert res.params["temp_c"] == pytest.approx(124.59, abs=0.01)
    assert res.params["holiday"] == pytest.approx(-624.01, abs=0.01)
    eff = nb.effect_table(res, {"temp_c": 5, "wind_kmh": 10})
    assert eff.loc["temp_c", "effect"] == pytest.approx(622.9, abs=0.1)
    assert eff.loc["wind_kmh", "ci_high"] == pytest.approx(-280.5, abs=0.5)
    path = nb.coef_path(day, "temp_c", {"một biến": "cnt ~ temp_c", "+ năm": "cnt ~ temp_c + C(year)"})
    assert path.round(2).tolist() == [161.97, 155.36]
