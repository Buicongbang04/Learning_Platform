import re
import numpy as np
import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)

ROWS = [
    {"name": "bf16", "bpc": 1.00, "memory_mib": 1000, "tok_s": 30},
    {"name": "int8", "bpc": 1.01, "memory_mib": 700, "tok_s": 10},
    {"name": "nf4", "bpc": 1.05, "memory_mib": 450, "tok_s": 25},
    {"name": "fp4", "bpc": 1.08, "memory_mib": 450, "tok_s": 25},
    {"name": "q4", "bpc": 1.04, "memory_mib": 400, "tok_s": 40},
    {"name": "q2", "bpc": 1.30, "memory_mib": 300, "tok_s": 40},
    {"name": "fast", "bpc": 1.10, "memory_mib": 900, "tok_s": 60},
]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("qwen_deploy.ipynb")


def test_gguf_to_hf_name(nb):
    assert nb.gguf_to_hf_name("token_embd.weight") == "model.embed_tokens.weight"
    assert nb.gguf_to_hf_name("output_norm.weight") == "model.norm.weight"
    assert nb.gguf_to_hf_name("output.weight") == "lm_head.weight"
    assert nb.gguf_to_hf_name("blk.0.attn_q.bias") == "model.layers.0.self_attn.q_proj.bias"
    assert nb.gguf_to_hf_name("blk.23.attn_output.weight") == "model.layers.23.self_attn.o_proj.weight"
    assert nb.gguf_to_hf_name("blk.5.ffn_gate.weight") == "model.layers.5.mlp.gate_proj.weight"
    assert nb.gguf_to_hf_name("blk.5.ffn_down.weight") == "model.layers.5.mlp.down_proj.weight"
    assert nb.gguf_to_hf_name("blk.7.attn_norm.weight") == "model.layers.7.input_layernorm.weight"
    assert nb.gguf_to_hf_name("blk.7.ffn_norm.weight") == "model.layers.7.post_attention_layernorm.weight"
    with pytest.raises(KeyError):
        nb.gguf_to_hf_name("blk.0.attn_qkv.weight")


def test_load_gguf_state_dict(nb, tmp_path):
    import gguf
    import gguf.quants

    rng = np.random.default_rng(0)
    emb = rng.normal(size=(16, 64)).astype(np.float32)
    down = rng.normal(size=(64, 256)).astype(np.float32)
    norm = rng.normal(size=(64,)).astype(np.float32)
    path = tmp_path / "tiny-qwen2.gguf"
    w = gguf.GGUFWriter(str(path), "qwen2")
    w.add_tensor("token_embd.weight", gguf.quants.quantize(emb, gguf.GGMLQuantizationType.Q8_0),
                 raw_dtype=gguf.GGMLQuantizationType.Q8_0)
    w.add_tensor("blk.0.ffn_down.weight", gguf.quants.quantize(down, gguf.GGMLQuantizationType.Q4_0),
                 raw_dtype=gguf.GGMLQuantizationType.Q4_0)
    w.add_tensor("blk.0.attn_norm.weight", norm)
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()
    state, types = nb.load_gguf_state_dict(path)
    assert set(state) == {"model.embed_tokens.weight", "model.layers.0.mlp.down_proj.weight", "model.layers.0.input_layernorm.weight"}
    assert types == {"model.embed_tokens.weight": "Q8_0", "model.layers.0.mlp.down_proj.weight": "Q4_0",
                     "model.layers.0.input_layernorm.weight": "F32"}
    e, d, n = state["model.embed_tokens.weight"], state["model.layers.0.mlp.down_proj.weight"], state["model.layers.0.input_layernorm.weight"]
    assert isinstance(e, torch.Tensor) and e.dtype == torch.float32
    assert e.shape == (16, 64) and d.shape == (64, 256) and n.shape == (64,)
    assert np.abs(e.numpy() - emb).max() < 0.03, "Q8_0: sai số nhỏ"
    rel = np.linalg.norm(d.numpy() - down) / np.linalg.norm(down)
    assert 0.02 < rel < 0.2, "Q4_0: sai số cỡ 4 bit, và phải là giá trị đã giải lượng tử"
    np.testing.assert_array_equal(n.numpy(), norm)


def test_pareto_front(nb):
    front = nb.pareto_front(ROWS, minimize=("bpc", "memory_mib"), maximize=("tok_s",))
    assert front == ["bf16", "int8", "q4", "q2", "fast"]
    assert nb.pareto_front(ROWS, minimize=("bpc", "memory_mib")) == ["bf16", "int8", "q4", "q2"]
    assert nb.pareto_front(ROWS, minimize=("bpc",)) == ["bf16"]
    tie = [{"name": "a", "x": 1}, {"name": "b", "x": 1}]
    assert nb.pareto_front(tie, minimize=("x",)) == ["a", "b"], "bằng nhau thì không trội nhau"


def test_pick_config(nb):
    assert nb.pick_config(ROWS, 4096, 0.02, 1.0) == "bf16"
    assert nb.pick_config(ROWS, 800, 0.02, 1.0) == "int8"
    assert nb.pick_config(ROWS, 800, 0.05, 1.0) == "q4"
    assert nb.pick_config(ROWS, 350, 0.05, 1.0) is None
    assert nb.pick_config(ROWS, 400, 0.05, 1.0) == "q4", "đúng bằng ngân sách vẫn đạt"
    assert nb.pick_config(ROWS, 500, 0.10, 1.0) == "q4"
    assert nb.pick_config(ROWS, 500, 0.40, 1.0) == "q2", "hoà tốc độ thì chọn dòng ít bộ nhớ hơn"
    rows = [dict(r, cpu=r["tok_s"] if r["name"] != "int8" else 99) for r in ROWS]
    assert nb.pick_config(rows, 4096, 0.02, 1.0, speed_key="cpu") == "int8"


def test_report():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo portfolio: ít nhất 600 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng kết quả"
    assert re.search(r"bpc|bits?[- ]per[- ]char", doc, re.I), "dùng bits-per-character làm thước đo chất lượng"
    assert re.search(r"cpu", doc, re.I) and re.search(r"gpu", doc, re.I), "báo cáo phải có cả CPU và GPU"
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc)
    for img in images:
        if not img.startswith("http"):
            assert (ex.path("REPORT.md").parent / img).exists(), f"không thấy tệp hình {img}"
