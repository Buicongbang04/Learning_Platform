import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("stacking.ipynb")


class Spy:
    """Model "gián điệp": dự đoán = thời điểm lớn nhất nó thấy lúc fit (chia 1e6 để nằm trong (0, 1))."""

    def fit(self, X, y):
        self.seen_ = float(np.max(X["t"]))
        return self

    def predict_proba(self, X):
        p = np.full(len(X), self.seen_ / 1e6)
        return np.column_stack([1 - p, p])


def shuffled_frame(n: int = 103, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = rng.permutation(np.arange(1, n + 1)) * 1000.0
    return pd.DataFrame({"t": t, "x": rng.normal(size=n)}, index=rng.permutation(np.arange(5000, 5000 + n)))


def test_expanding_folds_never_look_ahead(nb):
    df = shuffled_frame()
    folds = nb.expanding_folds(df.t.to_numpy(), n_folds=4)
    assert len(folds) == 4
    t = df.t.to_numpy()
    previous_fit = 0
    for fit_idx, pred_idx in folds:
        assert t[fit_idx].max() < t[pred_idx].min()
        assert len(fit_idx) > previous_fit           # cửa sổ mở rộng dần
        previous_fit = len(fit_idx)
    predicted = np.concatenate([p for _, p in folds])
    assert len(predicted) == len(set(predicted.tolist()))
    # khối đầu tiên (khoảng 1/5 dữ liệu sớm nhất) không bao giờ được dự đoán
    assert len(df) - len(predicted) == pytest.approx(len(df) / 5, abs=1)
    assert set(t[np.setdiff1d(np.arange(len(df)), predicted)]) == set(np.sort(t)[: len(df) - len(predicted)])


def test_oof_uses_only_the_past(nb):
    df = shuffled_frame(seed=1)
    y = np.arange(len(df)) % 2
    folds = nb.expanding_folds(df.t.to_numpy(), n_folds=4)
    oof = nb.oof_predictions({"spy": Spy, "spy2": Spy}, df[["t", "x"]], y, folds)
    assert list(oof.columns) == ["spy", "spy2"]
    assert oof.index.equals(df.index)
    done = oof.spy.notna().to_numpy()
    assert done.sum() == sum(len(p) for _, p in folds)
    # mỗi dòng được dự đoán bởi model chỉ thấy dữ liệu trước nó
    assert (oof.spy[done] * 1e6 < df.t[done]).all()
    assert oof.spy[~done].isna().all()


def test_oof_is_not_in_sample(nb):
    """Model học thuộc lòng (1-NN trên id) cho OOF kém hẳn dự đoán trong mẫu."""
    from sklearn.neighbors import KNeighborsClassifier

    rng = np.random.default_rng(2)
    n = 400
    df = pd.DataFrame({"t": np.arange(n, dtype=float), "id": rng.permutation(n).astype(float)})
    y = rng.integers(0, 2, n)
    folds = nb.expanding_folds(df.t.to_numpy(), n_folds=3)
    oof = nb.oof_predictions({"knn": lambda: KNeighborsClassifier(n_neighbors=1)}, df[["id"]], y, folds)
    done = oof.knn.notna().to_numpy()
    accuracy = ((oof.knn[done] > 0.5).astype(int) == y[done]).mean()
    assert accuracy < 0.65


def make_base_predictions(n: int, seed: int):
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=n)
    y = (rng.random(n) < 1 / (1 + np.exp(-(2 * signal - 1)))).astype(int)
    good = 1 / (1 + np.exp(-(2 * signal - 1 + rng.normal(0, 0.5, n))))
    noise = rng.random(n)
    return pd.DataFrame({"good": good, "noise": noise}), y


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_meta_model_trusts_the_informative_model(nb, seed):
    oof, y = make_base_predictions(4000, seed)
    oof.iloc[:500] = np.nan                        # khối đầu chưa có OOF
    meta = nb.fit_meta(oof, y)
    assert isinstance(meta, LogisticRegression)
    good, noise = meta.coef_.ravel()
    assert good > 0.6
    assert abs(noise) < 0.15 * good


def test_meta_features_are_logits(nb):
    P = np.array([[0.5, 0.25], [0.9, 1.0]])
    Z = nb.to_logit(P)
    assert Z[0, 0] == pytest.approx(0.0)
    assert Z[0, 1] == pytest.approx(np.log(1 / 3))
    assert Z[1, 0] == pytest.approx(np.log(9))
    assert np.isfinite(Z).all()                    # 1.0 phải được kẹp lại, không ra vô cực


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300
