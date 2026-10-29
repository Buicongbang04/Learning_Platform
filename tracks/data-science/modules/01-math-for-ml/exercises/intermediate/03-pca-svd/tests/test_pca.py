import numpy as np
import pandas as pd
import pytest
from sklearn.decomposition import PCA

from testkit import ROOT, Exercise

ex = Exercise(__file__)

FEATURES = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm",
            "product_photos_qty", "product_name_lenght", "product_description_lenght"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("pca_products.ipynb")


def correlated(n: int = 400, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    size = rng.normal(size=n)
    text = rng.normal(size=n)
    return np.column_stack([
        size + 0.3 * rng.normal(size=n), 2 * size + 0.5 * rng.normal(size=n), size + 0.8 * rng.normal(size=n),
        text + 0.4 * rng.normal(size=n), 0.5 * text + 0.6 * rng.normal(size=n),
    ]) + np.array([5.0, -3.0, 0.0, 10.0, 1.0])


def test_prepare_product_matrix(nb):
    products = pd.DataFrame({
        "product_id": ["a", "b", "c", "d"],
        "product_weight_g": [100.0, 1000.0, np.nan, 10000.0],
        "product_length_cm": [10.0, 20.0, 30.0, 40.0],
        "product_height_cm": [2.0, 5.0, 5.0, 30.0],
        "product_width_cm": [10.0, 15.0, 20.0, 40.0],
        "product_photos_qty": [1.0, 2.0, 3.0, 1.0],
        "product_name_lenght": [40.0, 50.0, 60.0, 30.0],
        "product_description_lenght": [200.0, 800.0, 100.0, 3000.0],
    })
    X = nb.prepare_product_matrix(products)
    assert X.shape == (3, 7)                                   # dòng thiếu bị bỏ
    expected = np.log1p(products.dropna()[FEATURES].to_numpy())
    expected = (expected - expected.mean(axis=0)) / expected.std(axis=0)
    assert X == pytest.approx(expected)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_pca_matches_sklearn(nb, seed):
    X = correlated(seed=seed)
    out = nb.pca_svd(X, 3)
    ref = PCA(n_components=3).fit(X)
    assert out["components"].shape == (3, 5) and out["scores"].shape == (400, 3)
    assert out["explained_variance"] == pytest.approx(ref.explained_variance_, rel=1e-8)
    assert out["explained_variance_ratio"] == pytest.approx(ref.explained_variance_ratio_, rel=1e-8)
    assert out["mean"] == pytest.approx(X.mean(axis=0))
    for i in range(3):   # thành phần chính chỉ xác định tới dấu
        sign = np.sign(out["components"][i] @ ref.components_[i])
        assert out["components"][i] == pytest.approx(sign * ref.components_[i], abs=1e-8)
        assert out["scores"][:, i] == pytest.approx(sign * ref.transform(X)[:, i], abs=1e-7)


def test_sign_convention(nb):
    out = nb.pca_svd(correlated(seed=3), 5)
    for v in out["components"]:
        assert v[np.argmax(np.abs(v))] > 0       # phần tử lớn nhất theo trị tuyệt đối mang dấu dương


def test_components_are_covariance_eigenvectors(nb):
    X = correlated(seed=4)
    out = nb.pca_svd(X, 5)
    C = np.cov(X, rowvar=False)
    V = out["components"]
    assert V @ V.T == pytest.approx(np.eye(5), abs=1e-10)                  # trực chuẩn
    for v, lam in zip(V, out["explained_variance"]):
        assert C @ v == pytest.approx(lam * v, abs=1e-8)                   # C v = λ v
    assert np.all(np.diff(out["explained_variance"]) <= 0)


def test_reconstruct(nb):
    X = correlated(seed=5)
    full = nb.pca_svd(X, 5)
    assert nb.reconstruct(full) == pytest.approx(X)                       # đủ k = d: khôi phục chính xác
    errs = [np.mean((nb.reconstruct(nb.pca_svd(X, k)) - X) ** 2) for k in range(1, 6)]
    assert all(a >= b for a, b in zip(errs, errs[1:]))
    # sai số tái tạo = tổng variance của các thành phần bị bỏ (chia lại theo n − 1 và d)
    ev = full["explained_variance"]
    assert errs[1] == pytest.approx(ev[2:].sum() * (len(X) - 1) / len(X) / X.shape[1], rel=1e-8)


def test_n_components_for(nb):
    evr = np.array([0.5, 0.3, 0.15, 0.05])
    assert nb.n_components_for(evr, 0.5) == 1
    assert nb.n_components_for(evr, 0.79) == 2
    assert nb.n_components_for(evr, 0.9) == 3
    assert nb.n_components_for(evr, 1.0) == 4


def test_real_olist_products(nb):
    path = ROOT / "data" / "raw" / "olist_products_dataset.csv"
    if not path.exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    X = nb.prepare_product_matrix(pd.read_csv(path))
    assert X.shape == (32340, 7)
    out = nb.pca_svd(X, 7)
    assert out["explained_variance_ratio"][:2] == pytest.approx([0.3589, 0.1764], abs=5e-4)
    assert nb.n_components_for(out["explained_variance_ratio"], 0.9) == 5
    pc1 = out["components"][0]
    assert np.all(pc1[:4] > 0.3) and np.all(np.abs(pc1[4:]) < 0.15)       # PC1 = "kích thước" sản phẩm
