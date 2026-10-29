import numpy as np
import onnx
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from testkit import Exercise

ex = Exercise(__file__)

NUMERIC = ["promised_days", "delivery_days", "delay_days", "approve_hours", "n_items", "price", "freight"]
CATEGORICAL = ["customer_state", "payment_type"]


def make_orders(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    promised = rng.uniform(10, 40, n)
    delivery = np.clip(promised + rng.normal(-10, 8, n), 1, None)
    df = pd.DataFrame({
        "promised_days": promised, "delivery_days": delivery, "delay_days": delivery - promised,
        "approve_hours": rng.exponential(10, n), "n_items": rng.integers(1, 4, n).astype(float),
        "price": rng.lognormal(4.5, 0.8, n), "freight": rng.lognormal(2.8, 0.5, n),
        "customer_state": rng.choice(["SP", "RJ", "MG", "BA"], n),
        "payment_type": rng.choice(["credit_card", "boleto", "voucher"], n),
    })
    df.loc[rng.random(n) < 0.05, "approve_hours"] = np.nan
    return df


def labels(df: pd.DataFrame, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (0.3 * df.delay_days + rng.normal(0, 2, len(df)) > -1).astype(int).to_numpy()


def preprocessor():
    return ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])


@pytest.fixture(scope="module")
def train():
    df = make_orders(2000, seed=0)
    return df, labels(df, 1)


@pytest.fixture(scope="module")
def logreg(train):
    df, y = train
    return make_pipeline(preprocessor(), LogisticRegression(max_iter=1000)).fit(df, y)


@pytest.fixture(scope="module")
def forest(train):
    df, y = train
    return make_pipeline(preprocessor(), RandomForestClassifier(n_estimators=30, max_depth=6, random_state=0)).fit(df, y)


@pytest.fixture(scope="module")
def mod():
    return ex.module("onnx_export.py")


def test_export_writes_valid_onnx(mod, logreg, tmp_path):
    path = mod.export_onnx(logreg, NUMERIC, CATEGORICAL, tmp_path / "model.onnx")
    assert path.exists() and path.stat().st_size > 0
    model = onnx.load(path)
    onnx.checker.check_model(model)
    assert [i.name for i in model.graph.input] == NUMERIC + CATEGORICAL   # một input mỗi cột, đúng tên


def test_logreg_parity(mod, logreg, tmp_path):
    path = mod.export_onnx(logreg, NUMERIC, CATEGORICAL, tmp_path / "lr.onnx")
    test = make_orders(3000, seed=2)
    got = mod.onnx_predict_proba(path, test, NUMERIC, CATEGORICAL)
    want = logreg.predict_proba(test)[:, 1]
    assert got.shape == (3000,)
    assert np.max(np.abs(got - want)) < 1e-5


def test_unknown_category_and_missing_values(mod, logreg, tmp_path):
    path = mod.export_onnx(logreg, NUMERIC, CATEGORICAL, tmp_path / "lr.onnx")
    test = make_orders(200, seed=3)
    test.loc[:9, "customer_state"] = "XX"                     # bang chưa thấy lúc train
    test.loc[10:19, "approve_hours"] = np.nan
    test.loc[20:29, "payment_type"] = None                    # thiếu: điền "missing" như lúc train
    got = mod.onnx_predict_proba(path, test, NUMERIC, CATEGORICAL)
    want = logreg.predict_proba(test.fillna({"payment_type": "missing"}))[:, 1]
    assert np.max(np.abs(got - want)) < 1e-5


def test_single_row_and_input_not_modified(mod, logreg, tmp_path):
    path = mod.export_onnx(logreg, NUMERIC, CATEGORICAL, tmp_path / "lr.onnx")
    test = make_orders(5, seed=4)
    before = test.copy()
    one = mod.onnx_predict_proba(path, test.iloc[[2]], NUMERIC, CATEGORICAL)
    pd.testing.assert_frame_equal(test, before)
    assert one.shape == (1,)
    assert one[0] == pytest.approx(logreg.predict_proba(test.iloc[[2]])[0, 1], abs=1e-5)


def test_tree_model_parity_report(mod, forest, tmp_path):
    path = mod.export_onnx(forest, NUMERIC, CATEGORICAL, tmp_path / "rf.onnx")
    test = make_orders(2000, seed=5)
    report = mod.parity_report(forest, path, test, NUMERIC, CATEGORICAL)
    assert set(report) >= {"max_abs_diff", "share_within_1e-5", "n"}
    assert report["n"] == 2000
    # float32 trong ONNX có thể làm vài điểm sát ngưỡng chia rẽ sang nhánh khác: không đòi tuyệt đối
    assert report["share_within_1e-5"] >= 0.99
    assert 0 <= report["max_abs_diff"] < 0.5


def test_parity_report_on_logreg(mod, logreg, tmp_path):
    path = mod.export_onnx(logreg, NUMERIC, CATEGORICAL, tmp_path / "lr.onnx")
    report = mod.parity_report(logreg, path, make_orders(500, seed=6), NUMERIC, CATEGORICAL)
    assert report["n"] == 500
    assert report["share_within_1e-5"] == pytest.approx(1.0)
    assert report["max_abs_diff"] < 1e-5


def test_report_written():
    text = ex.read("REPORT.md")
    assert "TODO" not in text
    assert len(text.split()) >= 350
