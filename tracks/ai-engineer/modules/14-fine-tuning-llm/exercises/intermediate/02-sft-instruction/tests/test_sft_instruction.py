import math
import unicodedata

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("sft_instruction.ipynb")


class FakeTokenizer:
    """Mỗi ký tự một token, template kiểu ChatML với thẻ một token."""

    pad_token_id = 0
    tags = {"<s>": 1, "</s>": 2}

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False, **kwargs):
        text = "".join(f"<s>{m['role']}\n{m['content']}</s>\n" for m in messages)
        return text + ("<s>assistant\n" if add_generation_prompt else "")

    def __call__(self, text, add_special_tokens=True):
        ids, i = [], 0
        while i < len(text):
            for tag, tid in self.tags.items():
                if text.startswith(tag, i):
                    ids.append(tid)
                    i += len(tag)
                    break
            else:
                ids.append(min(ord(text[i]), 120))
                i += 1
        return {"input_ids": ids}


def test_pasted_data_functions(nb):
    tok = FakeTokenizer()
    chat = [{"role": "user", "content": "hỏi"}, {"role": "assistant", "content": "đáp"}]
    out = nb.tokenize_chat(chat, tok)
    kept = [t for t, label in zip(out["input_ids"], out["labels"]) if label != -100]
    assert len(kept) == len("đáp") + 2 and kept[-2:] == [2, ord("\n")], "dán đúng tokenize_chat của bài Basic 02"
    batch = nb.pad_batch([out, {"input_ids": [5], "labels": [5]}], pad_token_id=0)
    assert batch["labels"][1, 1:].eq(-100).all() and batch["attention_mask"][1].tolist()[:2] == [1, 0]


def test_token_budget_batches(nb):
    lengths = [5, 100, 7, 30, 6, 31, 250, 8]
    batches = nb.token_budget_batches(lengths, max_tokens=64, seed=0)
    flat = sorted(i for b in batches for i in b)
    assert flat == list(range(8)), "mỗi mẫu đúng một lần"
    for b in batches:
        assert len(b) == 1 or len(b) * max(lengths[i] for i in b) <= 64
    as_sets = sorted(tuple(sorted(b)) for b in batches)
    assert as_sets == [(0, 2, 4, 7), (1,), (3, 5), (6,)], "sort theo độ dài rồi gom tham lam"
    assert nb.token_budget_batches(lengths, 64, seed=0) == batches, "cùng seed, cùng thứ tự"
    orders = {tuple(map(tuple, nb.token_budget_batches(lengths, 64, seed=s))) for s in range(6)}
    assert len(orders) > 1, "seed trộn thứ tự các batch"
    assert all(b == sorted(b, key=lambda i: (lengths[i], i)) for b in batches), "trong batch giữ thứ tự độ dài"


def test_token_budget_batches_ties_are_stable(nb):
    batches = nb.token_budget_batches([4, 4, 4, 4, 4], max_tokens=8, seed=0)
    assert sorted(map(tuple, batches)) == [(0, 1), (2, 3), (4,)]


def tiny_model():
    from transformers import Qwen2Config, Qwen2ForCausalLM

    torch.manual_seed(0)
    return Qwen2ForCausalLM(Qwen2Config(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=1,
                                        num_attention_heads=4, num_key_value_heads=2, initializer_range=0.5))


def test_heldout_nll_is_token_weighted(nb):
    model = tiny_model().train()
    b1 = {"input_ids": torch.tensor([[3, 4, 5, 6, 7, 8]]), "attention_mask": torch.ones(1, 6, dtype=torch.long),
          "labels": torch.tensor([[-100, -100, 5, 6, 7, 8]])}
    b2 = {"input_ids": torch.tensor([[9, 10, 11, 0], [12, 13, 0, 0]]),
          "attention_mask": torch.tensor([[1, 1, 1, 0], [1, 1, 0, 0]]),
          "labels": torch.tensor([[-100, 10, 11, -100], [-100, 13, -100, -100]])}
    nll, n = nb.heldout_nll(model, [b1, b2])
    assert n == 4 + 3
    assert not model.training, "đo ở chế độ eval"
    total = 0.0
    with torch.no_grad():
        for b in (b1, b2):
            logits = model(input_ids=b["input_ids"], attention_mask=b["attention_mask"]).logits
            for r in range(logits.shape[0]):
                for t in range(1, logits.shape[1]):
                    if b["labels"][r, t] != -100:
                        total -= torch.log_softmax(logits[r, t - 1], -1)[b["labels"][r, t]].item()
    assert nll == pytest.approx(total / 7, rel=1e-5)
    with torch.no_grad():
        mean_of_means = (model(**b1).loss.item() + model(**b2).loss.item()) / 2
    assert nll != pytest.approx(mean_of_means, rel=1e-4), "trung bình theo token, không phải trung bình các batch"
    assert math.isfinite(nll)


def test_normalize_and_exact_match(nb):
    assert nb.normalize_answer("  Nguyên  phân. ") == "nguyên phân"
    assert nb.normalize_answer(unicodedata.normalize("NFD", "A: Hữu ích!")) == "a hữu ích"
    assert nb.normalize_answer("(B) 1,5 kg") == "b 1 5 kg"
    assert nb.exact_match("Nguyên phân.", "nguyên phân")
    assert not nb.exact_match("Đáp án là nguyên phân", "nguyên phân")
    assert not nb.exact_match("", "a")


def test_is_short_answer(nb):
    def chat(user, answer):
        return [{"role": "system", "content": "S"}, {"role": "user", "content": user},
                {"role": "assistant", "content": answer}]

    q = "Quá trình phân chia hạt nhân gọi là gì? Lựa chọn: - giảm phân - rụng trứng - Nguyên phân\n Trả lời:"
    assert nb.is_short_answer(chat(q, "nguyên phân."))
    assert not nb.is_short_answer(chat(q, "phân bào"))
    assert not nb.is_short_answer(chat(q, "..."))
    long_answer = "giảm phân " * 7
    assert not nb.is_short_answer(chat(long_answer * 2, long_answer)), "đáp án dài hơn 60 ký tự"
    assert nb.is_short_answer(chat(long_answer * 2, long_answer), max_chars=100)
