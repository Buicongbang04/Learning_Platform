import re
import types
from dataclasses import dataclass

import pytest
import torch
import torch.nn as nn
from testkit import Exercise
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("gpt_vi.ipynb")


@dataclass
class TinyConfig:
    vocab_size: int = 300
    block_size: int = 8
    n_layer: int = 1
    n_head: int = 1
    n_embd: int = 4
    dropout: float = 0.0


class TinyGPT(nn.Module):
    def __init__(self, config: TinyConfig):
        super().__init__()
        self.config = config
        self.tok_emb = nn.Embedding(config.vocab_size, config.n_embd)
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)
        self.lm_head.weight = self.tok_emb.weight

    def forward(self, idx, targets=None):
        return self.lm_head(self.tok_emb(idx)), None


GPT_MODULE = types.SimpleNamespace(GPT=TinyGPT, GPTConfig=TinyConfig)


def tokenizer():
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    tok.train_from_iterator(["Hà Nội là thủ đô của Việt Nam. " * 20],
                            trainers.BpeTrainer(vocab_size=300, initial_alphabet=pre_tokenizers.ByteLevel.alphabet()))
    return tok


def test_checkpoint_format(nb, tmp_path):
    torch.manual_seed(0)
    config = TinyConfig(n_embd=6)
    model = TinyGPT(config)
    path = tmp_path / "ckpt.pt"
    tok = tokenizer()
    nb.save_checkpoint(path, model, config, tok, 1234, {"bpc": 1.5})
    raw = torch.load(path, weights_only=True)
    assert raw["format"] == "gpt-mini-v1" and raw["step"] == 1234 and raw["metrics"] == {"bpc": 1.5}
    assert raw["config"] == {"vocab_size": 300, "block_size": 8, "n_layer": 1, "n_head": 1, "n_embd": 6, "dropout": 0.0}
    assert set(raw["state_dict"]) == set(model.state_dict())
    assert isinstance(raw["tokenizer"], str) and Tokenizer.from_str(raw["tokenizer"]).get_vocab() == tok.get_vocab()


def test_checkpoint_round_trip(nb, tmp_path):
    torch.manual_seed(1)
    config = TinyConfig(n_embd=5)
    model = TinyGPT(config).train()
    tok = tokenizer()
    path = tmp_path / "ckpt.pt"
    nb.save_checkpoint(path, model, config, tok, 7, {"bpc": 2.0, "ppl": 90.0})
    loaded, tok2, info = nb.load_checkpoint(path, GPT_MODULE)
    assert isinstance(loaded, TinyGPT) and not loaded.training
    assert loaded.config == config
    assert loaded.lm_head.weight is loaded.tok_emb.weight
    idx = torch.tensor([[1, 2, 3]])
    torch.testing.assert_close(loaded(idx)[0], model(idx)[0])
    text = "Hà Nội là thủ đô"
    assert tok2.encode(text).ids == tok.encode(text).ids
    assert info == {"step": 7, "metrics": {"bpc": 2.0, "ppl": 90.0}}


def test_checkpoint_rejects_other_format(nb, tmp_path):
    path = tmp_path / "other.pt"
    torch.save({"format": "something-else", "config": {}, "state_dict": {}, "tokenizer": "", "step": 0, "metrics": {}}, path)
    with pytest.raises(ValueError):
        nb.load_checkpoint(path, GPT_MODULE)


def test_distinct_n(nb):
    assert nb.distinct_n([1, 2, 3, 4], 1) == 1.0
    assert nb.distinct_n([5, 5, 5, 5], 1) == 0.25
    assert nb.distinct_n([1, 2, 1, 2, 1, 2], 2) == pytest.approx(2 / 5)
    assert nb.distinct_n([1, 2, 3, 1, 2, 3, 4], 3) == pytest.approx(4 / 5)
    assert nb.distinct_n([1], 2) == 0.0


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo portfolio: ít nhất 600 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng kết quả"
    assert re.search(r"bpc|bits?[- ]per[- ]char", doc, re.I), "báo cáo phải dùng bits-per-character để so với LSTM"
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc)
    for img in images:
        if not img.startswith("http"):
            assert (ex.path("REPORT.md").parent / img).exists(), f"không thấy tệp hình {img}"
