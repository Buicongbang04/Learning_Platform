import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("churn_eda.ipynb")


def tiny_raw():
    return pd.DataFrame({
        "customerID": ["a", "b", "c", "d", "e", "f", "g", "h"],
        "SeniorCitizen": [0, 1, 0, 0, 1, 0, 0, 0],
        "tenure": [0, 1, 6, 7, 12, 24, 48, 72],
        "Contract": ["M", "M", "M", "M", "One", "One", "Two", "Two"],
        "MonthlyCharges": [20.0, 70.0, 80.0, 90.0, 50.0, 60.0, 30.0, 100.0],
        "TotalCharges": [" ", "70", "480.5", "630", "600", "1440", "1440", "7200"],
        "Churn": ["No", "Yes", "Yes", "No", "Yes", "No", "No", "No"],
    })


def test_clean_telco(nb):
    raw = tiny_raw()
    before = raw.copy()
    df = nb.clean_telco(raw)
    pd.testing.assert_frame_equal(raw, before)
    assert df["TotalCharges"].dtype == float
    assert np.isnan(df.loc[0, "TotalCharges"]) and df.loc[2, "TotalCharges"] == 480.5
    assert df["SeniorCitizen"].tolist() == ["No", "Yes", "No", "No", "Yes", "No", "No", "No"]
    assert df["churned"].dtype == bool
    assert df["churned"].tolist() == [False, True, True, False, True, False, False, False]
    assert list(df.columns[:len(raw.columns)]) == list(raw.columns)


def test_clean_telco_rejects_non_numeric(nb):
    raw = tiny_raw()
    raw.loc[3, "TotalCharges"] = "abc"
    with pytest.raises((ValueError, TypeError)):
        nb.clean_telco(raw)


def test_add_tenure_band(nb):
    raw = tiny_raw()
    df = nb.add_tenure_band(raw)
    assert "tenure_band" not in raw.columns
    assert df["tenure_band"].astype(str).tolist() == ["0-6", "0-6", "0-6", "7-12", "7-12", "13-24", "25-48", "49-72"]
    assert list(df["tenure_band"].cat.categories) == ["0-6", "7-12", "13-24", "25-48", "49-72"]
    assert df["tenure_band"].cat.ordered


def test_rate_table(nb):
    df = nb.clean_telco(tiny_raw())
    out = nb.rate_table(df, "Contract")
    assert list(out.columns) == ["n", "churned", "rate", "share_of_n", "share_of_churned", "lift"]
    assert out.index.name == "Contract"
    assert list(out.index) == ["M", "One", "Two"]                     # rate 0.5, 0.5, 0: sắp giảm dần, ổn định
    assert out["n"].tolist() == [4, 2, 2] and out["churned"].tolist() == [2, 1, 0]
    assert out.loc["M", "rate"] == pytest.approx(0.5)
    assert out.loc["One", "share_of_n"] == pytest.approx(0.25)
    assert out.loc["M", "share_of_churned"] == pytest.approx(2 / 3)
    assert out.loc["M", "lift"] == pytest.approx(0.5 / (3 / 8))
    assert out["share_of_churned"].sum() == pytest.approx(1.0)


def test_rate_table_categorical_drops_empty_groups(nb):
    df = nb.add_tenure_band(nb.clean_telco(tiny_raw()))
    df = df[df.tenure < 40]                                           # hai nhóm cuối không còn khách
    out = nb.rate_table(df, "tenure_band")
    assert set(out.index.astype(str)) == {"0-6", "7-12", "13-24"}
    assert out.loc["0-6", "rate"] == pytest.approx(2 / 3)


def test_compare_numeric(nb):
    df = nb.clean_telco(tiny_raw())
    out = nb.compare_numeric(df, "TotalCharges")
    assert list(out.columns) == ["n", "mean", "median", "std", "iqr", "skew"]
    assert list(out.index) == [False, True] and out.index.name == "churned"
    stay = df.loc[~df.churned, "TotalCharges"].dropna()
    assert out.loc[False, "n"] == 4                                   # khách tenure 0 (NaN) không được đếm
    assert out.loc[False, "median"] == pytest.approx(stay.median())
    assert out.loc[False, "std"] == pytest.approx(stay.std())
    assert out.loc[False, "iqr"] == pytest.approx(stay.quantile(0.75) - stay.quantile(0.25))
    assert out.loc[True, "mean"] == pytest.approx((70 + 480.5 + 600) / 3)


@pytest.fixture(scope="module")
def real_raw():
    return pd.read_csv(ex.dataset("telco-churn") / "WA_Fn-UseC_-Telco-Customer-Churn.csv")


def prepared(nb, raw):
    return nb.add_tenure_band(nb.clean_telco(raw))


def test_real_clean(nb, real_raw):
    real = prepared(nb, real_raw)
    assert len(real) == 7043 and real.churned.sum() == 1869
    assert real.TotalCharges.isna().sum() == 11
    assert (real.loc[real.TotalCharges.isna(), "tenure"] == 0).all()


def test_real_rate_tables(nb, real_raw):
    real = prepared(nb, real_raw)
    contract = nb.rate_table(real, "Contract")
    assert list(contract.index) == ["Month-to-month", "One year", "Two year"]
    assert contract.loc["Month-to-month", "rate"] == pytest.approx(0.4271, abs=1e-4)
    assert contract.loc["Month-to-month", "share_of_churned"] == pytest.approx(0.8855, abs=1e-4)
    band = nb.rate_table(real, "tenure_band")
    assert band.index[0] == "0-6" and band.loc["0-6", "rate"] == pytest.approx(0.5294, abs=1e-4)
    senior = nb.rate_table(real, "SeniorCitizen")
    assert senior.loc["Yes", "share_of_churned"] == pytest.approx(0.2547, abs=1e-4)


def test_real_compare_numeric(nb, real_raw):
    real = prepared(nb, real_raw)
    tenure = nb.compare_numeric(real, "tenure")
    assert tenure["median"].tolist() == [38.0, 10.0]
    total = nb.compare_numeric(real, "TotalCharges")
    assert total["n"].tolist() == [5163, 1869]
    assert total.loc[True, "median"] == pytest.approx(703.55)
