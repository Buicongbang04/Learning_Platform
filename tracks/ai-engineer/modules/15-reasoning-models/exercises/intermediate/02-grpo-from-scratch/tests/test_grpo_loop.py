import math

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("grpo_loop.ipynb")


@pytest.fixture(scope="module")
def tiny():
    from transformers import Qwen2Config, Qwen2ForCausalLM

    cfg = Qwen2Config(vocab_size=40, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                      num_key_value_heads=2, max_position_embeddings=64, tie_word_embeddings=True)
    torch.manual_seed(0)
    return Qwen2ForCausalLM(cfg).eval()


# ---------- Dán từ Basic 01, 03 ----------

def test_pasted_pieces(nb):
    adv = nb.group_advantages(torch.tensor([1.0, 1.0, 0.0, 1.0]), group_size=2)
    assert adv[0] == 0 and adv[1] == 0 and adv[3] > 0 > adv[2]
    old = torch.zeros(1, 1)
    out = nb.clipped_surrogate(old + math.log(1.5), old, torch.tensor([1.0]))
    assert out.item() == pytest.approx(1.2, rel=1e-5)
    assert nb.kl_k3(torch.tensor([-1.0]), torch.tensor([-1.0])).item() == 0.0
    assert nb.total_reward("Half of 36 is 18, so \\boxed{18}.", "18") == pytest.approx(1.2)
    assert nb.correctness_reward("\\boxed{17 or 18}", "18") == 0.0


# ---------- Mask phần completion ----------

def test_completion_mask(nb):
    ids = torch.tensor([[5, 6, 2, 9, 9], [7, 2, 2, 9, 9], [5, 5, 5, 5, 5], [3, 4, 5, 6, 1]])
    mask = nb.completion_mask(ids, stop_ids={2, 1})
    expected = torch.tensor([[1, 1, 1, 0, 0], [1, 1, 0, 0, 0], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1]])
    assert torch.equal(mask.long(), expected), "giữ token dừng đầu tiên (model phải học dừng), bỏ mọi thứ sau nó"
    assert mask.shape == ids.shape


# ---------- Log-prob của completion ----------

def _batch():
    torch.manual_seed(3)
    prompt = torch.randint(3, 40, (3, 6))
    prompt_mask = torch.ones_like(prompt)
    prompt_mask[0, :2] = 0
    prompt[0, :2] = 0
    prompt_mask[2, :4] = 0
    prompt[2, :4] = 0
    completion = torch.randint(3, 40, (3, 5))
    completion_mask = torch.tensor([[1, 1, 1, 1, 1], [1, 1, 0, 0, 0], [1, 1, 1, 0, 0]])
    return prompt, prompt_mask, completion, completion_mask


def _manual(model, prompt, prompt_mask, completion, completion_mask):
    out = torch.zeros(completion.shape, dtype=torch.float64)
    for b in range(prompt.shape[0]):
        p = prompt[b][prompt_mask[b].bool()]
        seq = torch.cat([p, completion[b]])[None]
        with torch.no_grad():
            logp = torch.log_softmax(model(input_ids=seq).logits[0].double(), -1)
        for t in range(completion.shape[1]):
            if completion_mask[b, t]:
                out[b, t] = logp[len(p) + t - 1, completion[b, t]]
    return out


def test_completion_logprobs_match_unpadded_forward(nb, tiny):
    prompt, prompt_mask, completion, completion_mask = _batch()
    got = nb.completion_logprobs(tiny, prompt, prompt_mask, completion, completion_mask)
    assert got.shape == completion.shape
    expected = _manual(tiny, prompt, prompt_mask, completion, completion_mask)
    torch.testing.assert_close(got.double(), expected, rtol=1e-4, atol=1e-4)
    assert torch.all(got[completion_mask == 0] == 0), "vị trí ngoài mask trả 0"


def test_completion_logprobs_has_gradient(nb, tiny):
    prompt, prompt_mask, completion, completion_mask = _batch()
    tiny.zero_grad()
    nb.completion_logprobs(tiny, prompt, prompt_mask, completion, completion_mask).sum().backward()
    grad = tiny.model.embed_tokens.weight.grad
    assert grad is not None and grad.abs().sum() > 0, "không bọc trong no_grad: loss cần gradient qua log-prob"
    tiny.zero_grad()


class _Spy(torch.nn.Module):
    def __init__(self, inner):
        super().__init__()
        self.inner = inner
        self.kwargs = []

    def forward(self, **kwargs):
        self.kwargs.append(kwargs)
        return self.inner(**kwargs)


def test_completion_logprobs_only_keeps_needed_logits(nb, tiny):
    prompt, prompt_mask, completion, completion_mask = _batch()
    spy = _Spy(tiny)
    nb.completion_logprobs(spy, prompt, prompt_mask, completion, completion_mask)
    assert len(spy.kwargs) == 1
    kw = spy.kwargs[0]
    assert kw.get("logits_to_keep") == completion.shape[1] + 1, \
        "chỉ cần logits của C + 1 vị trí cuối: với vocab 151 936, logits cả chuỗi chiếm phần lớn VRAM"
    assert torch.equal(kw["attention_mask"][:, :prompt.shape[1]].long(), prompt_mask.long())


def test_completion_logprobs_temperature(nb, tiny):
    prompt, prompt_mask, completion, completion_mask = _batch()
    got = nb.completion_logprobs(tiny, prompt, prompt_mask, completion, completion_mask, temperature=0.7)
    p = prompt[1]
    seq = torch.cat([p, completion[1]])[None]
    with torch.no_grad():
        logp = torch.log_softmax(tiny(input_ids=seq).logits[0].double() / 0.7, -1)
    assert got[1, 0].item() == pytest.approx(logp[len(p) - 1, completion[1, 0]].item(), abs=1e-4), \
        "log-prob theo đúng phân phối đã lấy mẫu: chia logits cho temperature"
