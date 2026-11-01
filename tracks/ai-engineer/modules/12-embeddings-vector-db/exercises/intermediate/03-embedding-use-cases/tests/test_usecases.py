import numpy as np
import pytest
from llmkit import FakeLLM

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("usecases.ipynb")


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def circle(degrees):
    r = np.deg2rad(np.asarray(degrees, dtype=float))
    return np.stack([np.cos(r), np.sin(r)], axis=1).astype(np.float32)


# ---------- phân loại ----------


def test_class_centroids(nb):
    x = unit([[1, 0], [0, 1], [3, 0], [0, 2]])
    y = np.array([0, 1, 0, 1])
    c = nb.class_centroids(x, y, 3)
    assert c.shape == (3, 2) and c.dtype == np.float32
    np.testing.assert_allclose(c, [[1, 0], [0, 1], [0, 0]], atol=1e-6), "lớp 2 không có mẫu: vector 0"
    c = nb.class_centroids(circle([0, 90, 180]), np.array([0, 0, 1]), 2)
    np.testing.assert_allclose(c[0], [2 ** -0.5, 2 ** -0.5], rtol=1e-5), "trung bình rồi chuẩn hoá L2"


def test_predict_centroid(nb):
    c = circle([0, 90])
    assert nb.predict_centroid(c, circle([10, 80, 30, 200])).tolist() == [0, 1, 0, 1]


def test_knn_vote_and_ties(nb):
    train = circle([0, 5, 10, 30, 40, 100])
    labels = np.array([0, 0, 1, 1, 1, 2])
    assert nb.knn_predict(train, labels, circle([2]), 1, 3).tolist() == [0]
    assert nb.knn_predict(train, labels, circle([2]), 3, 3).tolist() == [0], "2 phiếu lớp 0 thắng 1 phiếu lớp 1"
    assert nb.knn_predict(train, labels, circle([20]), 5, 3).tolist() == [1], "3 phiếu thắng 2 phiếu"
    # k = 4 quanh 18°: 0°, 5° (lớp 0) và 10°, 30° (lớp 1) hoà 2-2; tổng cosine lớp 1 lớn hơn
    assert nb.knn_predict(train, labels, circle([18]), 4, 3).tolist() == [1]
    # hoà phiếu và hoà tổng cosine: nhãn nhỏ
    sym = circle([-10, 10])
    assert nb.knn_predict(sym, np.array([1, 0]), circle([0]), 2, 2).tolist() == [0]
    assert nb.knn_predict(sym, np.array([0, 1]), circle([0]), 2, 2).tolist() == [0]


def test_knn_batches_consistent(nb):
    rng = np.random.default_rng(0)
    train = unit(rng.normal(size=(200, 8)))
    labels = rng.integers(0, 3, 200)
    x = unit(rng.normal(size=(37, 8)))
    a = nb.knn_predict(train, labels, x, 7, 3, batch=5)
    b = nb.knn_predict(train, labels, x, 7, 3, batch=1000)
    assert a.tolist() == b.tolist() and len(a) == 37


def test_knn_on_fake_embeddings(nb):
    fake = FakeLLM(dim=256)
    docs = ["giảng viên dạy rất hay nhiệt tình", "thầy giảng dễ hiểu vui tính", "phòng học nóng máy lạnh hỏng",
            "cơ sở vật chất xuống cấp phòng nóng"]
    train = unit(fake.embed(docs))
    labels = np.array([0, 0, 1, 1])
    q = unit(fake.embed(["phòng học quá nóng", "thầy dạy nhiệt tình"]))
    assert nb.knn_predict(train, labels, q, 1, 2).tolist() == [1, 0]


# ---------- trùng lặp ----------


def test_near_duplicates_order_and_batch(nb):
    x = circle([0, 1, 50, 50.5, 120, 0])
    pairs = nb.near_duplicates(x, 0.999, batch=2)
    assert [(i, j) for i, j, _ in pairs] == [(0, 5), (2, 3), (0, 1), (1, 5)]
    assert pairs[0][2] == pytest.approx(1.0, abs=1e-6) and isinstance(pairs[0][2], float)
    assert all(i < j for i, j, _ in pairs)
    assert nb.near_duplicates(x, 0.999, batch=100) == pairs
    exact_dup = np.eye(3, dtype=np.float32)[[0, 0, 1]]
    assert nb.near_duplicates(exact_dup, 1.0) == [(0, 1, 1.0)], "ngưỡng tính cả cosine bằng đúng threshold"


def test_nearest_in(nb):
    ref = circle([0, 90, 180])
    idx, sim = nb.nearest_in(ref, circle([10, 100, 45]), batch=2)
    assert idx.tolist() == [0, 1, 0], "45° cách đều 0° và 90°: chỉ số nhỏ"
    np.testing.assert_allclose(sim, np.cos(np.deg2rad([10, 10, 45])), atol=1e-6)


# ---------- bất thường ----------


def test_knn_anomaly_scores(nb):
    ref = circle([0, 10, 20])
    s = nb.knn_anomaly_scores(ref, circle([10, 90]), k=2, batch=1)
    want_10 = 1 - (1 + np.cos(np.deg2rad(10))) / 2
    want_90 = 1 - (np.cos(np.deg2rad(70)) + np.cos(np.deg2rad(80))) / 2
    np.testing.assert_allclose(s, [want_10, want_90], atol=1e-6)
    assert s[1] > s[0]


def test_auroc_hand_and_ties(nb):
    assert nb.auroc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]) == pytest.approx(0.75)
    assert nb.auroc([0.5, 0.5, 0.5, 0.5], [0, 1, 0, 1]) == pytest.approx(0.5), "bằng điểm tính một nửa"
    assert nb.auroc([0.9, 0.8, 0.1], [1, 1, 0]) == pytest.approx(1.0)
    assert nb.auroc([0.9, 0.8, 0.1], [0, 0, 1]) == pytest.approx(0.0), "điểm cao là bất thường, không đảo chiều"
    rng = np.random.default_rng(1)
    s = rng.normal(size=300)
    lab = rng.integers(0, 2, 300)
    from sklearn.metrics import roc_auc_score
    assert nb.auroc(s, lab) == pytest.approx(roc_auc_score(lab, s))


# ---------- gợi ý ----------


def test_recommend(nb):
    x = circle([0, 10, 20, 90, 100, 200])
    assert nb.recommend(x, [0], 2) == [1, 2], "không gợi ý lại mục đã thích"
    assert nb.recommend(x, [0, 3], 3) == [2, 1, 4], "hồ sơ là trung bình chuẩn hoá (45°)"
    out = nb.recommend(x, [5], 10)
    assert 5 not in out and len(out) == 5 and all(isinstance(i, int) for i in out)
