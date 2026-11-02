import gzip
import math
import re
import time
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("framework.ipynb")


def blobs(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """10 cụm Gauss trong 784 chiều (cùng shape với MNIST): dữ liệu nhỏ, học được, sinh trong test."""
    centers = np.random.default_rng(0).normal(0, 1, (10, 784))
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 10, n)
    X = centers[y] + 5 * rng.normal(size=(n, 784))
    return X.astype(np.float32), y.astype(np.int64)


def memorize_trap(seed: int) -> tuple[np.ndarray, ...]:
    """Train: 1000 điểm, 40% nhãn bị đổi ngẫu nhiên. Val: 300 điểm train đầu (nhiễu rất nhỏ), nhãn sạch.

    Lúc đầu model học tâm cụm nên val cao; train lâu thì nó thuộc lòng cả nhãn sai, val tụt (bản tham chiếu:
    0.92 ở epoch 1, còn 0.65 ở epoch 5). Chỉ model nạp lại trọng số tốt nhất mới giữ được mức cao.
    """
    centers = np.random.default_rng(0).normal(0, 1, (10, 784))
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 10, 1000)
    X = (centers[y] + 3 * rng.normal(size=(1000, 784))).astype(np.float32)
    noisy = np.where(rng.random(1000) < 0.4, rng.integers(0, 10, 1000), y)
    Xv = (X[:300] + 0.1 * rng.normal(size=(300, 784))).astype(np.float32)
    return X, noisy.astype(np.int64), Xv, y[:300].astype(np.int64)


_FIT: dict[str, tuple] = {}


def fitted(nb) -> tuple:
    """Train một lần trên dữ liệu sinh cho nhiều test; gọi trong thân test để starter FAIL chứ không ERROR."""
    if "run" not in _FIT:
        X, y = blobs(1000, 1)
        Xv, yv = blobs(300, 2)
        model = nb.build_model(0)
        history = nb.fit(model, X, y, Xv, yv, epochs=4)
        _FIT["run"] = (model, history, Xv, yv)
    return _FIT["run"]


def test_history_format(nb):
    _, history, _, _ = fitted(nb)
    assert {"train_loss", "val_acc"} <= set(history)
    n = len(history["train_loss"])
    assert 1 <= n <= 4, "mỗi phần tử một epoch đã chạy, không quá `epochs`"
    assert len(history["val_acc"]) == n
    for v in history["train_loss"] + history["val_acc"]:
        assert isinstance(v, float) and math.isfinite(v)
    assert all(0.0 <= v <= 1.0 for v in history["val_acc"])


def test_fit_learns(nb):
    _, history, _, _ = fitted(nb)
    assert max(history["val_acc"]) >= 0.8, "10 cụm tách được: val accuracy phải trên 0.8 sau 4 epoch"
    if len(history["train_loss"]) > 1:
        assert history["train_loss"][-1] < history["train_loss"][0]


def test_evaluate_range(nb):
    model, _, Xv, yv = fitted(nb)
    acc = nb.evaluate(model, Xv, yv)
    assert isinstance(acc, float) and 0.0 <= acc <= 1.0


def test_fit_keeps_best_weights(nb):
    X, y, Xv, yv = memorize_trap(1)
    model = nb.build_model(0)
    history = nb.fit(model, X, y, Xv, yv, epochs=6)
    assert nb.evaluate(model, Xv, yv) == pytest.approx(max(history["val_acc"]), abs=1e-9), (
        "kết thúc fit, model phải mang trọng số (kể cả running stats) của epoch có val accuracy cao nhất"
    )


def test_evaluate_is_eval_mode(nb):
    model, _, Xv, yv = fitted(nb)
    full = nb.evaluate(model, Xv, yv)
    assert nb.evaluate(model, Xv, yv) == full, "evaluate không được đổi trạng thái của model"
    # Ở chế độ eval, mỗi ảnh được dự đoán độc lập: chia tập thành nhóm 5 ảnh vẫn ra cùng số đúng.
    # (BatchNorm dùng thống kê của batch hay dropout còn bật thì không.)
    chunks = sum(nb.evaluate(model, Xv[i:i + 5], yv[i:i + 5]) * 5 for i in range(0, len(yv), 5))
    assert chunks == pytest.approx(full * len(yv), abs=1e-6)


def test_same_seed_same_history(nb):
    X, y = blobs(400, 3)
    Xv, yv = blobs(100, 4)
    runs = [nb.fit(nb.build_model(5), X, y, Xv, yv, epochs=2) for _ in range(2)]
    assert runs[0]["train_loss"] == runs[1]["train_loss"]
    assert runs[0]["val_acc"] == runs[1]["val_acc"]


# ---------- Dữ liệu thật: tự skip nếu chưa tải MNIST ----------

def read_idx(path: Path) -> np.ndarray:
    data = gzip.open(path).read()
    ndim = data[3]
    shape = np.frombuffer(data, ">u4", ndim, offset=4).astype(int)
    return np.frombuffer(data, np.uint8, offset=4 + 4 * ndim).reshape(shape)


def test_mnist_test_accuracy(nb):
    root = ex.dataset("mnist")
    X = read_idx(root / "train-images-idx3-ubyte.gz").reshape(-1, 784).astype(np.float32) / 255
    y = read_idx(root / "train-labels-idx1-ubyte.gz").astype(np.int64)
    Xt = read_idx(root / "t10k-images-idx3-ubyte.gz").reshape(-1, 784).astype(np.float32) / 255
    yt = read_idx(root / "t10k-labels-idx1-ubyte.gz").astype(np.int64)
    try:
        from threadpoolctl import threadpool_limits   # đi kèm scikit-learn; thiếu thì chạy mặc định
        limit = threadpool_limits(4)
    except ImportError:
        limit = nullcontext()
    start = time.perf_counter()
    with limit:                            # ma trận nhỏ: nhiều luồng BLAS chỉ làm chậm
        model = nb.build_model(0)
        nb.fit(model, X[:50000], y[:50000], X[50000:], y[50000:], epochs=10)
        acc = nb.evaluate(model, Xt, yt)
    elapsed = time.perf_counter() - start
    assert acc >= 0.975, f"test accuracy {acc:.4f}"
    assert elapsed < 240, f"{elapsed:.0f} s; bản tham chiếu mất khoảng 25 s với 4 luồng BLAS"


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo portfolio: ít nhất 600 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng (ablation)"
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc)
    assert images, "chèn hình đường cong học, vd. ![](curves.png)"
    for img in images:
        if not img.startswith("http"):
            assert (ex.path("REPORT.md").parent / img).exists(), f"không thấy tệp hình {img}"
