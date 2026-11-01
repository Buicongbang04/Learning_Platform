import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)
VOCAB = 40


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("speculative.ipynb")


class ToyLM:
    """LM giả có trạng thái: logits phụ thuộc hai token cuối của trạng thái, như một KV cache."""

    def __init__(self, seed=0, copy_bias=0.0):
        rng = np.random.default_rng(seed)
        self.W = rng.normal(size=(VOCAB, VOCAB))
        self.U = rng.normal(size=(VOCAB, VOCAB))
        self.copy_bias = copy_bias
        self.tokens = []
        self.calls = 0
        self.extend_sizes = []

    def logits_for(self, ctx):
        prev = ctx[-2] if len(ctx) > 1 else 0
        z = self.W[ctx[-1]] + 0.5 * self.U[prev]
        if self.copy_bias:
            for i in range(len(ctx) - 2, -1, -1):
                if ctx[i] == ctx[-1]:
                    z = z.copy()
                    z[ctx[i + 1]] += self.copy_bias
                    break
        return z

    def reset(self, ids):
        self.calls += 1
        self.tokens = list(ids)
        return self.logits_for(self.tokens)

    def extend(self, ids):
        self.calls += 1
        self.extend_sizes.append(len(ids))
        rows = []
        for t in ids:
            self.tokens.append(int(t))
            rows.append(self.logits_for(self.tokens))
        return np.stack(rows)

    def truncate(self, length):
        assert 0 < length <= len(self.tokens), "truncate phải giữ một phần trạng thái hiện có"
        self.tokens = self.tokens[:length]


def reference_greedy(lm, prompt, n, eos=None):
    ctx, out = list(prompt), []
    while len(out) < n:
        t = int(np.argmax(lm.logits_for(ctx)))
        out.append(t)
        ctx.append(t)
        if t == eos:
            break
    return out


def oracle_drafter(lm):
    def draft(context, m):
        return reference_greedy(lm, context, m)
    return draft


def garbage_drafter(context, m):
    return [(context[-1] * 7 + i + 3) % VOCAB for i in range(m)]


PROMPT = [3, 17, 5, 22, 9, 3, 17]


# ---------- greedy ----------

@pytest.mark.parametrize("seed", [0, 1, 2])
def test_greedy_matches_reference_and_uses_one_call_per_token(nb, seed):
    lm = ToyLM(seed)
    out = nb.greedy_generate(lm, PROMPT, 25)
    assert out == reference_greedy(ToyLM(seed), PROMPT, 25)
    assert lm.calls == 25, "một reset rồi 24 extend, không gọi thừa sau token cuối"
    assert set(lm.extend_sizes) == {1}


def test_greedy_stops_at_eos(nb):
    lm = ToyLM(0)
    full = reference_greedy(lm, PROMPT, 30)
    eos = full[6]
    out = nb.greedy_generate(ToyLM(0), PROMPT, 30, eos_id=eos)
    assert out == full[:full.index(eos) + 1]
    assert nb.greedy_generate(ToyLM(0), PROMPT, 1) == full[:1]


# ---------- prompt lookup ----------

def test_prompt_lookup_examples(nb):
    assert nb.prompt_lookup_draft([1, 2, 3, 4, 1, 2], 3) == [3, 4, 1]
    assert nb.prompt_lookup_draft([5, 6, 9, 5, 6, 7, 5, 6], 2) == [7, 5], "lấy lần xuất hiện gần cuối nhất"
    assert nb.prompt_lookup_draft([8, 1, 2, 3, 9, 2, 3, 4, 1, 2, 3], 2, max_ngram=3) == [9, 2], "ưu tiên n-gram dài"
    assert nb.prompt_lookup_draft([1, 2, 3, 4, 5], 3) == []
    assert nb.prompt_lookup_draft([1, 2, 1, 2], 5) == [1, 2], "có thể ngắn hơn k"
    assert nb.prompt_lookup_draft([1, 2, 1, 2], 0) == []
    assert nb.prompt_lookup_draft([4], 3) == []
    assert nb.prompt_lookup_draft([7, 7], 3) == [7]


# ---------- speculative ----------

@pytest.mark.parametrize("seed", [0, 3])
@pytest.mark.parametrize("k", [1, 3, 5])
@pytest.mark.parametrize("drafter_kind", ["oracle", "garbage", "other_model", "lookup"])
def test_speculative_equals_target_greedy(nb, seed, k, drafter_kind):
    target = ToyLM(seed, copy_bias=4.0)
    expected = reference_greedy(ToyLM(seed, copy_bias=4.0), PROMPT, 40)
    drafter = {
        "oracle": oracle_drafter(ToyLM(seed, copy_bias=4.0)),
        "garbage": garbage_drafter,
        "other_model": oracle_drafter(ToyLM(seed + 100, copy_bias=4.0)),
        "lookup": nb.prompt_lookup_draft,
    }[drafter_kind]
    out, st = nb.speculative_generate(target, drafter, PROMPT, k, 40)
    assert out == expected, f"phải trùng greedy của target (drafter {drafter_kind}, k={k})"
    assert st["target_calls"] == target.calls
    assert 0 <= st["accepted"] <= st["proposed"]


def test_oracle_drafter_accepts_everything(nb):
    target = ToyLM(1)
    out, st = nb.speculative_generate(target, oracle_drafter(ToyLM(1)), PROMPT, 4, 41)
    assert len(out) == 41
    assert st["accepted"] == st["proposed"] == 32 and st["acceptance_rate"] == 1.0
    assert st["target_calls"] == 9 and st["rounds"] == 8, "1 reset + 8 lượt kiểm, mỗi lượt được 5 token"
    assert set(target.extend_sizes) == {5}


def test_garbage_drafter_costs_as_much_as_greedy(nb):
    target = ToyLM(2)
    out, st = nb.speculative_generate(target, garbage_drafter, PROMPT, 3, 20)
    assert out == reference_greedy(ToyLM(2), PROMPT, 20)
    assert st["accepted"] == 0 and st["acceptance_rate"] == 0.0
    assert st["target_calls"] == 20, "đoán sai hết thì mỗi lượt kiểm chỉ ra một token, như greedy"
    assert st["rounds"] == 19 and st["proposed"] == 17 * 3 + 2 + 1, "lượt cuối chỉ xin đoán số token còn lại"


def test_stats_counting_with_partial_acceptance(nb):
    expected = reference_greedy(ToyLM(0), PROMPT, 12)

    def half_right(context, m):
        good = reference_greedy(ToyLM(0), context, m)
        return good[:1] + [(g + 1) % VOCAB for g in good[1:]]

    target = ToyLM(0)
    out, st = nb.speculative_generate(target, half_right, PROMPT, 3, 12)
    assert out == expected
    assert st["rounds"] == 6 and st["proposed"] == 16 and st["accepted"] == 6
    assert st["target_calls"] == 7
    assert st["acceptance_rate"] == pytest.approx(6 / 16)


def test_drafter_sees_accepted_context_and_budget(nb):
    seen = []
    base = oracle_drafter(ToyLM(4))

    def spy(context, m):
        seen.append((list(context), m))
        return base(context, m)

    out, _ = nb.speculative_generate(ToyLM(4), spy, PROMPT, 4, 11)
    expected = reference_greedy(ToyLM(4), PROMPT, 11)
    assert out == expected
    for context, m in seen:
        produced = context[len(PROMPT):]
        assert context[:len(PROMPT)] == PROMPT and produced == expected[:len(produced)], \
            "ngữ cảnh đưa cho hàm đoán chỉ gồm prompt và token đã chắc chắn"
        assert m == min(4, 11 - len(produced)), "không xin đoán quá số token còn được sinh"


def test_overlong_draft_is_clipped_and_eos_inside_draft_stops(nb):
    full = reference_greedy(ToyLM(5), PROMPT, 30)
    eos = full[9]
    stop = full.index(eos) + 1

    def chatty(context, m):
        return reference_greedy(ToyLM(5), context, m + 5)

    out, st = nb.speculative_generate(ToyLM(5), chatty, PROMPT, 4, 30, eos_id=eos)
    assert out == full[:stop], "dừng ngay khi nhận eos, kể cả eos nằm trong khối đoán"
    out, _ = nb.speculative_generate(ToyLM(5), chatty, PROMPT, 4, 7)
    assert out == full[:7], "không vượt max_new_tokens dù hàm đoán trả dài hơn"


def test_rejected_tokens_do_not_leak_into_state(nb):
    target = ToyLM(6, copy_bias=4.0)
    nb.speculative_generate(target, garbage_drafter, PROMPT, 5, 15)
    expected = reference_greedy(ToyLM(6, copy_bias=4.0), PROMPT, 15)
    assert target.tokens[:len(PROMPT) + 14] == PROMPT + expected[:14], \
        "trạng thái target chỉ chứa token đã nhận"
