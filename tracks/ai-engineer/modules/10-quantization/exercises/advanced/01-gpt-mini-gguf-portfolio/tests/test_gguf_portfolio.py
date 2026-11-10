import re
import importlib.util
import json
import sys

import numpy as np
import pytest
import torch
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)
TEXT = ("Hà Nội là thủ đô của Việt Nam. Thành phố Hồ Chí Minh là thành phố lớn nhất. "
        "Sông Hồng chảy qua Hà Nội, sông Mê Kông chảy qua miền Tây Nam Bộ. ") * 20


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("gguf_portfolio.ipynb")


@pytest.fixture(scope="module")
def gpt_mini():
    path = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"
    spec = importlib.util.spec_from_file_location("m10_test_gpt_mini_a01", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tok():
    t = Tokenizer(models.BPE())
    t.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    t.decoder = decoders.ByteLevel()
    t.train_from_iterator([TEXT], trainers.BpeTrainer(vocab_size=300, initial_alphabet=pre_tokenizers.ByteLevel.alphabet()))
    return t


@pytest.fixture(scope="module")
def model(gpt_mini, tok):
    torch.manual_seed(0)
    m = gpt_mini.GPT(gpt_mini.GPTConfig(vocab_size=tok.get_vocab_size(), block_size=32, n_layer=2, n_head=2, n_embd=64))
    with torch.no_grad():
        for p in m.parameters():
            p.add_(torch.randn_like(p) * 0.02)
    return m.eval()


def field(reader, key):
    f = reader.fields[key]
    if len(f.data) == 1:
        v = f.parts[f.data[0]]
        return bytes(v).decode() if v.dtype == np.uint8 else v.tolist()[0]
    return [bytes(f.parts[i]).decode() if f.parts[i].dtype == np.uint8 else f.parts[i].tolist()[0] for i in f.data]


def test_tensor_names(nb):
    assert nb.gguf_tensor_name("tok_emb.weight") == "token_embd.weight"
    assert nb.gguf_tensor_name("pos_emb.weight") == "position_embd.weight"
    assert nb.gguf_tensor_name("ln_f.bias") == "output_norm.bias"
    assert nb.gguf_tensor_name("lm_head.weight") is None
    assert nb.gguf_tensor_name("blocks.3.ln1.weight") == "blk.3.attn_norm.weight"
    assert nb.gguf_tensor_name("blocks.0.attn.qkv.bias") == "blk.0.attn_qkv.bias"
    assert nb.gguf_tensor_name("blocks.11.attn.proj.weight") == "blk.11.attn_output.weight"
    assert nb.gguf_tensor_name("blocks.2.ln2.bias") == "blk.2.ffn_norm.bias"
    assert nb.gguf_tensor_name("blocks.1.mlp.fc.weight") == "blk.1.ffn_up.weight"
    assert nb.gguf_tensor_name("blocks.1.mlp.proj.bias") == "blk.1.ffn_down.bias"
    with pytest.raises(KeyError):
        nb.gguf_tensor_name("blocks.0.attn.mask")


def test_export_metadata_and_tokenizer(nb, model, tok, tmp_path):
    import gguf

    path = tmp_path / "tiny.gguf"
    nb.export_gguf(model, tok, path)
    r = gguf.GGUFReader(path)
    assert field(r, "general.architecture") == "gpt2"
    assert field(r, "gpt2.context_length") == 32
    assert field(r, "gpt2.embedding_length") == 64
    assert field(r, "gpt2.block_count") == 2
    assert field(r, "gpt2.feed_forward_length") == 256
    assert field(r, "gpt2.attention.head_count") == 2
    assert field(r, "gpt2.attention.layer_norm_epsilon") == pytest.approx(1e-5)
    assert field(r, "tokenizer.ggml.model") == "gpt2" and field(r, "tokenizer.ggml.pre") == "gpt-2"
    tokens = field(r, "tokenizer.ggml.tokens")
    vocab = tok.get_vocab()
    assert len(tokens) == len(vocab) and all(vocab[t] == i for i, t in enumerate(tokens)), "token theo đúng thứ tự id"
    merges = field(r, "tokenizer.ggml.merges")
    ref = json.loads(tok.to_str())["model"]["merges"]
    assert merges == [m if isinstance(m, str) else " ".join(m) for m in ref]
    assert field(r, "tokenizer.ggml.add_bos_token") in (False, 0)


def test_export_tensors(nb, model, tok, tmp_path):
    import gguf

    path = tmp_path / "tiny.gguf"
    nb.export_gguf(model, tok, path)
    r = gguf.GGUFReader(path)
    tensors = {t.name: t for t in r.tensors}
    assert len(tensors) == 4 + 12 * 2 and "output.weight" not in tensors
    sd = model.state_dict()
    for name, value in sd.items():
        target = nb.gguf_tensor_name(name)
        if target is None:
            continue
        t = tensors[target]
        assert t.tensor_type == gguf.GGMLQuantizationType.F32
        np.testing.assert_array_equal(np.asarray(t.data).reshape(value.shape), value.numpy())
    assert list(reversed(tensors["blk.0.attn_qkv.weight"].shape.tolist())) == [192, 64], "giữ shape (out, in) của PyTorch"


def test_export_f16(nb, model, tok, tmp_path):
    import gguf

    path = tmp_path / "tiny16.gguf"
    nb.export_gguf(model, tok, path, dtype="f16")
    r = gguf.GGUFReader(path)
    types = {t.name: t.tensor_type for t in r.tensors}
    assert types["blk.1.ffn_up.weight"] == gguf.GGMLQuantizationType.F16
    assert types["token_embd.weight"] == gguf.GGMLQuantizationType.F16
    assert types["blk.1.ffn_up.bias"] == gguf.GGMLQuantizationType.F32
    assert types["output_norm.weight"] == gguf.GGMLQuantizationType.F32
    nb.export_gguf(model, tok, tmp_path / "tiny32.gguf")
    assert path.stat().st_size < 0.7 * (tmp_path / "tiny32.gguf").stat().st_size


def test_sequence_nll(nb):
    logits = np.array([[2.0, 0.0, -1.0], [1000.0, 0.0, 0.0]], dtype=np.float32)
    targets = np.array([0, 1])
    z = logits[0].astype(np.float64)
    expected = -(z[0] - np.log(np.exp(z).sum())) + 1000.0
    out = nb.sequence_nll(logits, targets)
    assert isinstance(out, float) and np.isfinite(out)
    assert out == pytest.approx(expected, rel=1e-9)


def test_llama_cpp_matches_pytorch(nb, model, tok, tmp_path):
    llama_cpp = pytest.importorskip("llama_cpp", reason="cài bằng: uv sync --group llama")
    path = tmp_path / "tiny.gguf"
    nb.export_gguf(model, tok, path)
    llm = llama_cpp.Llama(model_path=str(path), n_ctx=32, n_batch=32, logits_all=True, n_threads=1, verbose=False)
    ids = tok.encode("Hà Nội là thủ đô của Việt Nam.").ids
    assert llm.tokenize("Hà Nội là thủ đô của Việt Nam.".encode(), add_bos=False, special=False) == ids
    llm.eval(ids)
    ours = np.asarray(llm.scores[:len(ids)])
    with torch.no_grad():
        ref = model(torch.tensor([ids]))[0][0].numpy()
    np.testing.assert_allclose(ours, ref, atol=2e-3, rtol=0)


def test_report():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo portfolio: ít nhất 600 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng kết quả"
    assert re.search(r"bpc|bits?[- ]per[- ]char", doc, re.I), "dùng bits-per-character làm thước đo chất lượng"
    assert re.search(r"gguf", doc, re.I), "báo cáo phải nói về tệp GGUF"
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc)
    for img in images:
        if not img.startswith("http"):
            assert (ex.path("REPORT.md").parent / img).exists(), f"không thấy tệp hình {img}"
