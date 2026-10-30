import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score

from testkit import Exercise

ex = Exercise(__file__)
FEATURES = ["contract_one_year", "contract_two_year", "tenure_years", "fiber_optic", "no_internet",
            "electronic_check", "monthly_charges_10", "senior", "tech_support", "paperless"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("churn_logit.ipynb")


def tiny_raw():
    return pd.DataFrame({
        "customerID": ["a", "b", "c", "d"],
        "Contract": ["Month-to-month", "One year", "Two year", "Month-to-month"],
        "tenure": [6, 24, 72, 0],
        "InternetService": ["Fiber optic", "DSL", "No", "DSL"],
        "PaymentMethod": ["Electronic check", "Mailed check", "Credit card (automatic)", "Electronic check"],
        "MonthlyCharges": [95.0, 55.5, 20.0, 45.0],
        "SeniorCitizen": [1, 0, 0, 0],
        "TechSupport": ["No", "Yes", "No internet service", "No"],
        "PaperlessBilling": ["Yes", "No", "No", "Yes"],
        "Churn": ["Yes", "No", "No", "Yes"],
    }, index=[10, 11, 12, 13])


def test_build_features(nb):
    raw = tiny_raw()
    before = raw.copy()
    X, y = nb.build_features(raw)
    pd.testing.assert_frame_equal(raw, before)
    assert list(X.columns) == FEATURES
    assert list(X.index) == [10, 11, 12, 13] and list(y.index) == [10, 11, 12, 13]
    assert X["contract_one_year"].tolist() == [0, 1, 0, 0]
    assert X["contract_two_year"].tolist() == [0, 0, 1, 0]
    assert X["tenure_years"].tolist() == pytest.approx([0.5, 2.0, 6.0, 0.0])
    assert X["fiber_optic"].tolist() == [1, 0, 0, 0] and X["no_internet"].tolist() == [0, 0, 1, 0]
    assert X["electronic_check"].tolist() == [1, 0, 0, 1]
    assert X["monthly_charges_10"].tolist() == pytest.approx([9.5, 5.55, 2.0, 4.5])
    assert X["senior"].tolist() == [1, 0, 0, 0]
    assert X["tech_support"].tolist() == [0, 1, 0, 0]                 # "No internet service" không phải "Yes"
    assert X["paperless"].tolist() == [1, 0, 0, 1]
    assert X["contract_two_year"].dtype.kind == "i" and X["tenure_years"].dtype.kind == "f"
    assert y.name == "churned" and y.tolist() == [1, 0, 0, 1] and y.dtype.kind == "i"


def synthetic(n=20_000, seed=3):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({"promo": rng.integers(0, 2, n), "age_10": rng.normal(4, 1, n)})
    logit = -1.0 + np.log(2.0) * X["promo"] - 0.5 * X["age_10"]          # odds ratio thật: 2.0 và e^-0.5
    y = pd.Series((rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int), name="y")
    return X, y


def test_fit_logit_recovers_odds_ratio(nb):
    X, y = synthetic()
    result = nb.fit_logit(X, y)
    assert set(result.params.index) == {"const", "promo", "age_10"}
    assert np.exp(result.params["promo"]) == pytest.approx(2.0, rel=0.1)
    assert result.params["age_10"] == pytest.approx(-0.5, abs=0.06)
    reference = sm.Logit(y, sm.add_constant(X)).fit(disp=0)            # không regularization
    assert result.params["promo"] == pytest.approx(reference.params["promo"], rel=1e-6)


def test_odds_ratio_table(nb):
    X, y = synthetic()
    result = sm.Logit(y, sm.add_constant(X)).fit(disp=0)
    out = nb.odds_ratio_table(result)
    assert list(out.columns) == ["coef", "odds_ratio", "ci_low", "ci_high", "p_value", "odds_change_pct"]
    assert list(out.index) == ["age_10", "promo"]                        # bỏ const, sắp odds_ratio tăng dần
    assert out.loc["promo", "odds_ratio"] == pytest.approx(np.exp(result.params["promo"]))
    assert out.loc["promo", "ci_low"] == pytest.approx(np.exp(result.conf_int().loc["promo", 0]))
    assert out.loc["promo", "ci_low"] < out.loc["promo", "odds_ratio"] < out.loc["promo", "ci_high"]
    assert out.loc["promo", "odds_change_pct"] == pytest.approx((out.loc["promo", "odds_ratio"] - 1) * 100)
    assert out.loc["promo", "p_value"] == pytest.approx(result.pvalues["promo"])


def test_decile_table(nb):
    y = [1, 0, 1, 0, 0, 0, 1, 0, 0, 0]
    score = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05]
    out = nb.decile_table(y, score, n_bins=5)
    assert list(out.columns) == ["n", "churners", "rate", "lift", "cum_capture"]
    assert out.index.name == "decile" and list(out.index) == [1, 2, 3, 4, 5]
    assert out["n"].tolist() == [2, 2, 2, 2, 2]
    assert out["churners"].tolist() == [1, 1, 0, 1, 0]
    assert out["lift"].tolist() == pytest.approx([0.5 / 0.3, 0.5 / 0.3, 0, 0.5 / 0.3, 0])
    assert out["cum_capture"].tolist() == pytest.approx([1 / 3, 2 / 3, 2 / 3, 1, 1])


def test_decile_table_unsorted_and_ties(nb):
    y = np.array([0, 1, 1, 0, 0, 1, 0])
    score = np.array([0.1, 0.9, 0.5, 0.5, 0.2, 0.95, 0.3])            # chưa sắp; hai khách hoà 0.5
    out = nb.decile_table(y, score, n_bins=2)
    # sắp giảm dần ổn định: 0.95(1) 0.9(1) 0.5(1, vị trí 2) | 0.5(0) 0.3(0) 0.2(0) 0.1(0); nhóm = i * 2 // 7 + 1
    assert out["n"].tolist() == [4, 3]
    assert out["churners"].tolist() == [3, 0]


@pytest.fixture(scope="module")
def telco_raw():
    return pd.read_csv(ex.dataset("telco-churn") / "WA_Fn-UseC_-Telco-Customer-Churn.csv")


def prepared(nb, raw):
    """Gọi hàm của người học trong test (không trong fixture) để starter FAIL chứ không ERROR."""
    X, y = nb.build_features(raw)
    X_train, X_test, y_train, y_test = nb.split_data(X, y)
    return X, y, X_test, y_test, nb.fit_logit(X_train, y_train)


def test_real_features(nb, telco_raw):
    X, y, *_ = prepared(nb, telco_raw)
    assert X.shape == (7043, 10) and y.sum() == 1869


def test_real_odds_ratios(nb, telco_raw):
    *_, result = prepared(nb, telco_raw)
    table = nb.odds_ratio_table(result)
    assert table.index[0] == "contract_two_year" and table.index[-1] == "fiber_optic"
    assert table.loc["contract_two_year", "odds_ratio"] == pytest.approx(0.251, abs=1e-3)
    assert table.loc["tenure_years", "odds_ratio"] == pytest.approx(0.684, abs=1e-3)
    assert table.loc["fiber_optic", "odds_change_pct"] == pytest.approx(95.4, abs=0.1)
    assert table.loc["monthly_charges_10", "p_value"] == pytest.approx(0.022, abs=1e-3)


def test_real_lift(nb, telco_raw):
    _, _, X_test, y_test, result = prepared(nb, telco_raw)
    p = result.predict(sm.add_constant(X_test, has_constant="add"))
    assert roc_auc_score(y_test, p) == pytest.approx(0.8407, abs=1e-4)
    deciles = nb.decile_table(y_test, p)
    assert deciles["n"].tolist() == [177] + [176] * 9
    assert deciles.loc[1, "churners"] == 130
    assert deciles.loc[1, "lift"] == pytest.approx(2.770, abs=1e-3)
    assert deciles.loc[3, "cum_capture"] == pytest.approx(0.662, abs=1e-3)
