import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("imagegen.ipynb")


def test_clip_score(nb):
    img = np.array([[3.0, 4.0], [1.0, 0.0], [0.0, 2.0]])
    txt = np.array([[6.0, 8.0], [-1.0, 0.0], [1.0, 1.0]])
    out = nb.clip_score(img, txt)
    assert out.shape == (3,)
    np.testing.assert_allclose(out, [100.0, 0.0, 100 / np.sqrt(2)], atol=1e-9)
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=(5, 16)), rng.normal(size=(5, 16))
    np.testing.assert_allclose(nb.clip_score(a * 7, b * 0.1), nb.clip_score(a, b), atol=1e-9)
    with pytest.raises(ValueError):
        nb.clip_score(np.ones((2, 3)), np.ones((3, 3)))


def test_time_call_counts_and_median(nb, monkeypatch):
    clock = iter([0.0, 1.0, 10.0, 10.5, 20.0, 29.0])   # ba lần đo: 1.0, 0.5, 9.0 -> trung vị 1.0
    monkeypatch.setattr(nb.time, "perf_counter", lambda: next(clock))
    calls, events = [], []
    result = nb.time_call(lambda: calls.append(1) or events.append("fn"), sync=lambda: events.append("sync"),
                          warmup=2, repeats=3)
    assert result == pytest.approx(1.0)
    assert len(calls) == 5
    assert events == ["fn", "fn"] + ["sync", "fn", "sync"] * 3, "sync ngay trước khi bắt và dừng đồng hồ, không sync lúc warmup"


def test_time_call_without_sync_and_errors(nb):
    assert nb.time_call(lambda: None, warmup=0, repeats=1) >= 0
    with pytest.raises(ValueError):
        nb.time_call(lambda: None, repeats=0)


def test_pareto_front(nb):
    rows = [{"cfg": "4 bước", "s": 0.42, "clip": 33.0}, {"cfg": "1 bước", "s": 0.24, "clip": 32.0},
            {"cfg": "2 bước", "s": 0.30, "clip": 31.5}, {"cfg": "4 bước + cfg", "s": 0.60, "clip": 32.5},
            {"cfg": "8 bước", "s": 0.80, "clip": 33.0}, {"cfg": "1 bước bản sao", "s": 0.24, "clip": 32.0}]
    assert [r["cfg"] for r in nb.pareto_front(rows, "s", "clip")] == ["1 bước", "1 bước bản sao", "4 bước"]
    assert nb.pareto_front([], "s", "clip") == []
