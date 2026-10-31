import types

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)
V = 7


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("generate.ipynb")


# ---------- decode ----------


class ScriptedLogits:
    """next_logits giả: token tiếp theo = (tổng chuỗi) mod V; ghi lại mọi chuỗi được đưa vào."""

    def __init__(self):
        self.calls: list[list[int]] = []

    def __call__(self, ids):
        self.calls.append(list(ids))
        out = np.zeros(V, dtype=np.float32)
        out[sum(ids) % V] = 1.0
        return out


def argmax_pick(logits, generated):
    return int(np.argmax(logits))


def test_decode_feeds_full_sequence(nb):
    f = ScriptedLogits()
    prompt = [1, 2]
    out = nb.decode(f, prompt, 4, argmax_pick)
    # 1+2=3 -> 3; 1+2+3=6 -> 6; 12 % 7 = 5; 17 % 7 = 3
    assert out == [3, 6, 5, 3]
    assert f.calls == [[1, 2], [1, 2, 3], [1, 2, 3, 6], [1, 2, 3, 6, 5]]
    assert prompt == [1, 2], "không sửa prompt_ids"
    assert all(type(t) is int for t in out)


def test_decode_stops_after_eos_inclusive(nb):
    out = nb.decode(ScriptedLogits(), [1, 2], 10, argmax_pick, eos_ids=[5])
    assert out == [3, 6, 5]
    assert nb.decode(ScriptedLogits(), [1, 2], 0, argmax_pick) == []
    assert nb.decode(ScriptedLogits(), (1, 2), 2, argmax_pick, eos_ids=(4,)) == [3, 6], "nhận tuple"


def test_decode_passes_generated_before_step(nb):
    seen = []

    def pick(logits, generated):
        seen.append(list(generated))
        return np.int64(len(generated))          # trả kiểu numpy: decode phải đổi sang int

    out = nb.decode(lambda ids: np.zeros(V), [9], 3, pick)
    assert seen == [[], [0], [0, 1]]
    assert out == [0, 1, 2] and all(type(t) is int for t in out)


# ---------- model Hugging Face giả ----------


torch = pytest.importorskip("torch")


class FakeCausalLM:
    """Model giả kiểu Hugging Face: logits ở vị trí t phụ thuộc mọi token tới t; past_key_values là các token đã thấy.

    Ghi lại input_ids và past_key_values của mỗi lần gọi để kiểm cách dùng KV cache.
    """

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, input_ids=None, past_key_values=None, use_cache=None, **kwargs):
        assert isinstance(input_ids, torch.Tensor) and input_ids.dtype == torch.long and input_ids.ndim == 2
        assert not torch.is_grad_enabled(), "gọi model trong torch.no_grad()"
        new = input_ids[0].tolist()
        prev = list(past_key_values) if past_key_values is not None else []
        self.calls.append({"input": new, "past": None if past_key_values is None else list(past_key_values),
                           "use_cache": use_cache})
        seq = prev + new
        logits = torch.zeros(1, len(new), V, dtype=torch.float64)
        for j in range(len(new)):
            prefix = seq[: len(prev) + j + 1]
            logits[0, j, (sum(prefix) * 3 + len(prefix)) % V] = 2.0
            logits[0, j, 0] += 0.5
        return types.SimpleNamespace(logits=logits, past_key_values=tuple(seq) if use_cache else None)


def test_hf_next_logits_full_sequence(nb):
    model = FakeCausalLM()
    fn = nb.hf_next_logits(model)
    out = fn([1, 2, 4])
    assert isinstance(out, np.ndarray) and out.dtype == np.float32 and out.shape == (V,)
    assert int(np.argmax(out)) == (7 * 3 + 3) % V and out[0] == pytest.approx(0.5), "logits của vị trí cuối"
    fn([1, 2, 4, 5])
    assert [c["input"] for c in model.calls] == [[1, 2, 4], [1, 2, 4, 5]], "không cache: luôn đưa cả chuỗi"
    assert all(c["past"] is None for c in model.calls)


def test_cached_feeds_only_new_tokens(nb):
    model = FakeCausalLM()
    out = nb.decode(nb.cached_next_logits(model), [4, 1, 2], 5, argmax_pick)
    ref = nb.decode(nb.hf_next_logits(FakeCausalLM()), [4, 1, 2], 5, argmax_pick)
    assert out == ref, "KV cache không được đổi kết quả"
    calls = model.calls
    assert calls[0]["input"] == [4, 1, 2] and calls[0]["past"] is None
    assert all(len(c["input"]) == 1 for c in calls[1:]), "sau lần đầu chỉ đưa token mới"
    assert all(c["use_cache"] for c in calls)
    assert calls[2]["past"] == [4, 1, 2, out[0]], "dùng past_key_values của lần gọi trước"


def test_cached_resets_on_new_prompt(nb):
    model = FakeCausalLM()
    fn = nb.cached_next_logits(model)
    a = fn([1, 2, 3])
    b = fn([1, 2, 3, 4, 5])                        # nối tiếp: đưa 2 token mới
    c = fn([6, 6])                                 # chuỗi khác: chạy lại từ đầu
    d = fn([6, 6])                                 # gọi lại cùng chuỗi: không có token mới, chạy lại từ đầu
    assert [x["input"] for x in model.calls] == [[1, 2, 3], [4, 5], [6, 6], [6, 6]]
    assert model.calls[2]["past"] is None and model.calls[3]["past"] is None
    plain = nb.hf_next_logits(FakeCausalLM())
    for got, ids in [(a, [1, 2, 3]), (b, [1, 2, 3, 4, 5]), (c, [6, 6]), (d, [6, 6])]:
        np.testing.assert_array_equal(got, plain(ids))


# ---------- fertility, distinct-n ----------


def test_fertility(nb):
    texts = ["xin chào bạn", "tôi là sinh viên giỏi"]
    assert nb.fertility(lambda t: len(t), texts) == pytest.approx((12 + 21) / 8), "tổng token / tổng từ, không trung bình tỉ lệ"
    assert nb.fertility(lambda t: 2 * len(t.split()), ["a b", "  c  "]) == pytest.approx(2.0)


def test_distinct_n(nb):
    texts = ["a b a b", "a b c"]
    # unigram: a b a b a b c -> 3 khác / 7
    assert nb.distinct_n(texts, 1) == pytest.approx(3 / 7)
    # bigram trong từng câu: (a b) (b a) (a b) | (a b) (b c) -> 3 khác / 5; không có cặp (b, a) nối hai câu
    assert nb.distinct_n(texts, 2) == pytest.approx(3 / 5)
    assert nb.distinct_n(["x y z", "u v"], 3) == pytest.approx(1.0)
    assert nb.distinct_n(["x"], 2) == 0.0 and nb.distinct_n([], 1) == 0.0
