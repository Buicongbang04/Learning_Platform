import importlib.util
import inspect
import re
import sys

import numpy as np
import pytest
import torch
from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)
GPT_FILE = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("broken_analysis.ipynb")


@pytest.fixture(scope="module")
def G():
    spec = importlib.util.spec_from_file_location("m08_a02_gpt", GPT_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tiny(G, seed=0):
    torch.manual_seed(seed)
    model = G.GPT(G.GPTConfig(vocab_size=25, block_size=12, n_layer=3, n_head=2, n_embd=12)).eval()
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith("bias"):
                p.add_(torch.randn_like(p) * 0.3)
            if "qkv.weight" in name or "emb" in name or name.endswith("proj.weight"):
                p.mul_(10)
    return model


def test_signatures_unchanged(nb):
    expected = {
        "cache_streams": ["model", "idx"],
        "lens_report": ["model", "idx"],
        "probe_with_controls": ["X", "y", "token_ids", "groups", "seed", "weight_decay"],
        "patch_resid": ["model", "idx", "source_streams", "layer", "pos"],
        "sae_report": ["sae", "acts"],
    }
    for name, params in expected.items():
        assert list(inspect.signature(getattr(nb, name)).parameters) == params, f"không đổi chữ ký của {name}"


def test_streams_consistent_with_model(nb, G):
    model = tiny(G)
    idx = torch.randint(25, (2, 8), generator=torch.Generator().manual_seed(1))
    logits, streams = nb.cache_streams(model, idx)
    assert sorted(streams) == [0, 1, 2]
    with torch.no_grad():
        x = model.tok_emb(idx) + model.pos_emb(torch.arange(8))
        for l, block in enumerate(model.blocks):
            x = block(x)
            torch.testing.assert_close(streams[l], x, atol=1e-5, rtol=1e-5, msg="cache_streams: kết quả không khớp model")
    report = nb.lens_report(model, idx)
    assert report[-1]["top1_agree"] == 1.0, "lens_report: tầng cuối phải trùng model"


def test_probe_controls_behaviour(nb):
    rng = np.random.default_rng(2)
    n_types, n = 40, 4000
    token_ids = rng.integers(0, n_types, n)
    X = np.eye(n_types)[token_ids] + rng.normal(0, 0.05, (n, n_types))
    y = (rng.random(n) < 0.4).astype(np.int64)
    groups = np.repeat(np.arange(n // 20), 20)
    out = nb.probe_with_controls(X, y, token_ids, groups, seed=0)
    assert set(out) == {"task", "control", "selectivity", "majority"}
    assert out["control"] > 0.9, "probe_with_controls: kết quả control không đúng trên dữ liệu kiểm tra"
    assert out["selectivity"] == pytest.approx(out["task"] - out["control"])
    assert abs(out["task"] - out["majority"]) < 0.05, "nhãn ngẫu nhiên: task không vượt majority"


def test_patch_resid_layer0_restores_clean(nb, G):
    model = tiny(G)
    g = torch.Generator().manual_seed(3)
    clean = torch.randint(25, (2, 9), generator=g)
    corrupt = clean.clone()
    corrupt[:, 5] = (clean[:, 5] + 7) % 25
    clean_logits, streams = nb.cache_streams(model, clean)
    with torch.no_grad():
        streams = dict(streams)
        streams["embed"] = model.tok_emb(clean) + model.pos_emb(torch.arange(9))
    out = nb.patch_resid(model, corrupt, streams, 0, 5)
    torch.testing.assert_close(out, clean_logits, atol=1e-5, rtol=1e-5, msg="patch_resid: kết quả không khớp phép thử")
    with torch.no_grad():
        corrupt_logits, _ = model(corrupt)
    same = nb.patch_resid(model, corrupt, streams, 2, 2)
    torch.testing.assert_close(same, corrupt_logits, atol=1e-5, rtol=1e-5, msg="patch_resid: kết quả không khớp phép thử")


def test_sae_report_reference_points(nb):
    g = torch.Generator().manual_seed(4)
    acts = torch.randn(500, 6, generator=g) * 2 + 5
    sae = nb.TopKSAE(6, 12, k=2)
    with torch.no_grad():
        sae.W_dec.zero_()
        sae.b_dec.copy_(acts.mean(0))
    rep = nb.sae_report(sae, acts)
    assert rep["fvu"] == pytest.approx(1.0, rel=1e-3), "sae_report: kết quả sai ở một điểm tham chiếu"
    with torch.no_grad():
        sae.b_dec.zero_()
    assert nb.sae_report(sae, acts)["fvu"] > 1.0


def test_bugs_written():
    doc = ex.read("BUGS.md")
    assert "TODO" not in doc
    assert len(re.findall(r"^## Bug \d", doc, re.M)) >= 4, "mỗi bug một mục `## Bug N: ...`"
    assert len(doc.split()) >= 300
