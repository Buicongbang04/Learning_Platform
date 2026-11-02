import hashlib
import json
import re

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

LABELS = ["negative", "neutral", "positive"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("suite.ipynb")


def data(seed=0, n=120):
    rng = np.random.default_rng(seed)
    y = [LABELS[i % 3] for i in range(n)]
    base = [t if rng.random() < 0.85 else LABELS[(LABELS.index(t) + 1) % 3] for t in y]
    return y, base


# ---------- thước đo dán từ Intermediate 02 ----------

def test_metrics_pasted(nb):
    y = ["negative", "negative", "neutral", "positive", "positive", "neutral"]
    p = ["negative", "positive", None, "positive", "positive", "neutral"]
    assert nb.macro_f1(y, p) == pytest.approx((2 / 3 + 2 / 3 + 0.8) / 3, abs=1e-12)
    y2, base = data(1, 60)
    assert nb.paired_bootstrap(y2, base, base, n_boot=100) == (0.0, 0.0, 0.0)


# ---------- cache_key ----------

def test_cache_key_definition(nb):
    prompt = [{"role": "system", "content": "Phân loại cảm xúc."}, {"role": "user", "content": "{sentence}"}]
    params = {"temperature": 0, "seed": 0, "num_predict": 8}
    expected = hashlib.sha256(json.dumps(
        {"prompt": prompt, "model": "qwen2.5:3b", "params": params, "item": "1969"},
        sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    key = nb.cache_key(prompt, "qwen2.5:3b", params, "1969")
    assert key == expected and re.fullmatch(r"[0-9a-f]{64}", key)


def test_cache_key_sensitivity(nb):
    params = {"temperature": 0, "seed": 0}
    k = nb.cache_key("p", "qwen2.5:3b", params, "1")
    assert k == nb.cache_key("p", "qwen2.5:3b", {"seed": 0, "temperature": 0}, "1"), "thứ tự khoá không quan trọng"
    others = {
        nb.cache_key("p ", "qwen2.5:3b", params, "1"),
        nb.cache_key("p", "qwen2.5:7b", params, "1"),
        nb.cache_key("p", "qwen2.5:3b", {"temperature": 0.2, "seed": 0}, "1"),
        nb.cache_key("p", "qwen2.5:3b", params, "2"),
        nb.cache_key({"text": "p"}, "qwen2.5:3b", params, "1"),
    }
    assert k not in others and len(others) == 5


# ---------- regression_gate ----------

def test_gate_identical_passes(nb):
    y, base = data()
    r = nb.regression_gate(y, base, list(base))
    assert isinstance(r, nb.GateResult)
    assert r.passed is True and r.reasons == [] and (r.diff, r.lo, r.hi) == (0.0, 0.0, 0.0)


def test_gate_uses_paired_bootstrap(nb):
    y, base = data(2)
    wrong = [i for i, (t, p) in enumerate(zip(y, base)) if t != p]
    cand = list(base)
    for i in wrong[:8]:
        cand[i] = y[i]
    r = nb.regression_gate(y, base, cand, n_boot=300, seed=5)
    assert (r.diff, r.lo, r.hi) == pytest.approx(nb.paired_bootstrap(y, base, cand, n_boot=300, seed=5))
    assert r.diff > 0 and r.passed


def test_gate_big_drop(nb):
    y, base = data(3)
    cand = [LABELS[(LABELS.index(t) + 2) % 3] if i % 2 == 0 else t for i, t in enumerate(base)]
    r = nb.regression_gate(y, base, cand, n_boot=300)
    assert not r.passed
    assert r.reasons[:2] == ["significant_drop", "point_drop"]


def test_gate_point_drop_only(nb):
    y, base = data(4)
    cand = list(base)
    down = up = 0
    for i, (t, p) in enumerate(zip(y, base)):
        if t == p and down < 7:
            cand[i] = LABELS[(LABELS.index(t) + 1) % 3]
            down += 1
        elif t != p and up < 3:
            cand[i] = t
            up += 1
    r = nb.regression_gate(y, base, cand, n_boot=300, max_drop=0.02)
    assert r.diff < -0.02 and r.hi >= 0, "dữ liệu test: tụt quá ngưỡng nhưng CI vẫn chạm 0"
    assert r.reasons == ["point_drop"]
    loose = nb.regression_gate(y, base, cand, n_boot=300, max_drop=0.2)
    assert loose.passed and loose.reasons == []


def test_gate_class_drop(nb):
    y = ["negative"] * 40 + ["neutral"] * 10 + ["positive"] * 40
    base = list(y)
    cand = list(y)
    for i in range(40, 43):
        cand[i] = "positive"      # hy sinh 3 câu neutral hiếm
    r = nb.regression_gate(y, base, cand, n_boot=200, max_drop=0.2)
    assert "class_drop:neutral" in r.reasons and not r.passed
    assert all(not x.startswith("class_drop:negative") for x in r.reasons)
    ok = nb.regression_gate(y, base, cand, n_boot=200, max_drop=0.2, class_max_drop=0.5)
    assert ok.passed


def test_gate_unparsed(nb):
    y, base = data(6)
    cand = list(base)
    cand[0] = None
    r = nb.regression_gate(y, base, cand, n_boot=200, max_drop=0.5, class_max_drop=0.5)
    assert r.reasons == ["more_unparsed"]
    r2 = nb.regression_gate(y, base, cand, n_boot=200, max_drop=0.5, class_max_drop=0.5, max_unparsed_increase=1)
    assert r2.passed


def test_gate_reason_order(nb):
    y = ["negative"] * 30 + ["neutral"] * 30 + ["positive"] * 30
    base = list(y)
    cand = ["negative"] * 30 + [None] * 30 + ["neutral"] * 30
    r = nb.regression_gate(y, base, cand, n_boot=200)
    assert r.reasons == ["significant_drop", "point_drop", "class_drop:neutral", "class_drop:positive",
                         "more_unparsed"]


# ---------- báo cáo ----------

def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 500, "báo cáo: ít nhất 500 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng kết quả"
