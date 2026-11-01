import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)

START, END = "<|im_start|>", "<|im_end|>"
SPECIAL = {START: 1000, END: 1001}
INV = {v: k for k, v in SPECIAL.items()}


class FakeTokenizer:
    """Tokenizer giả theo kiểu ChatML của Qwen2.5: mỗi ký tự một token, hai thẻ đặc biệt một token, có system mặc định."""

    pad_token_id = 0
    default_system = "Bạn là trợ lý."

    def __init__(self):
        self.encode_calls = 0

    def render(self, messages, add_generation_prompt):
        if not messages or messages[0]["role"] != "system":
            messages = [{"role": "system", "content": self.default_system}, *messages]
        text = "".join(f"{START}{m['role']}\n{m['content']}{END}\n" for m in messages)
        return text + (f"{START}assistant\n" if add_generation_prompt else "")

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False, **kwargs):
        assert tokenize is False, "bài này dựng chuỗi bằng template rồi tự tokenize"
        return self.render(messages, add_generation_prompt)

    def __call__(self, text, add_special_tokens=True):
        self.encode_calls += 1
        ids, i = [], 0
        while i < len(text):
            for tag, tid in SPECIAL.items():
                if text.startswith(tag, i):
                    ids.append(tid)
                    i += len(tag)
                    break
            else:
                ids.append(ord(text[i]))
                i += 1
        return {"input_ids": ids, "attention_mask": [1] * len(ids)}

    def decode(self, ids):
        return "".join(INV.get(i, chr(i)) for i in ids)


class UnstableTokenizer(FakeTokenizer):
    """Template đổi nội dung các lượt trước tuỳ độ dài hội thoại: tiền tố không ổn định."""

    def render(self, messages, add_generation_prompt):
        text = super().render(messages, add_generation_prompt)
        return f"[{len(messages)}]" + text


CHAT = [
    {"role": "user", "content": "Xin chào"},
    {"role": "assistant", "content": "Chào bạn"},
]
MULTI = [
    {"role": "system", "content": "S"},
    {"role": "user", "content": "1+1?"},
    {"role": "assistant", "content": "2"},
    {"role": "user", "content": "Nhân đôi?"},
    {"role": "assistant", "content": "4"},
]


@pytest.fixture(scope="module")
def sft():
    return ex.module("sft_data.py")


def kept(out):
    return [t for t, label in zip(out["input_ids"], out["labels"]) if label != -100]


def test_single_turn_labels_only_assistant(sft):
    tok = FakeTokenizer()
    out = sft.tokenize_chat(CHAT, tok)
    full = tok.render(CHAT, False)
    assert tok.decode(out["input_ids"]) == full, "input_ids là cả hội thoại theo template, kể cả system mặc định"
    assert len(out["labels"]) == len(out["input_ids"])
    assert tok.decode(kept(out)) == f"Chào bạn{END}\n", (
        "chỉ học phần trả lời của assistant cùng token kết thúc lượt; không học thẻ mở lượt, system, user")
    prefix = len(tok(tok.render(CHAT[:1], True))["input_ids"])
    assert all(label == -100 for label in out["labels"][:prefix])


def test_labels_are_not_shifted(sft):
    out = sft.tokenize_chat(CHAT, FakeTokenizer())
    pairs = [(t, label) for t, label in zip(out["input_ids"], out["labels"]) if label != -100]
    assert pairs and all(t == label for t, label in pairs), (
        "label tại vị trí t bằng input_ids[t]: model của Hugging Face tự dịch label khi tính loss")


def test_multi_turn_every_assistant_turn(sft):
    tok = FakeTokenizer()
    out = sft.tokenize_chat(MULTI, tok)
    assert tok.decode(kept(out)) == f"2{END}\n4{END}\n"
    text = tok.decode(out["input_ids"])
    assert text.count(START) == 5 and "Bạn là trợ lý." not in text, "có system riêng thì không chèn system mặc định"
    second_user = text.index("Nhân đôi?")
    assert all(label == -100 for label in out["labels"][second_user: second_user + 9])


def test_truncation_and_nothing_to_learn(sft):
    tok = FakeTokenizer()
    full = sft.tokenize_chat(CHAT, tok)
    cut = sft.tokenize_chat(CHAT, tok, max_length=len(full["input_ids"]) - 3)
    assert cut["input_ids"] == full["input_ids"][:-3] and cut["labels"] == full["labels"][:-3]
    prefix = len(tok(tok.render(CHAT[:1], True))["input_ids"])
    assert sft.tokenize_chat(CHAT, tok, max_length=prefix) is None, "cắt hết phần assistant thì không còn gì để học"
    assert sft.tokenize_chat([{"role": "user", "content": "hỏi"}], tok) is None


def test_unstable_template_raises(sft):
    with pytest.raises(ValueError):
        sft.tokenize_chat(MULTI, UnstableTokenizer())


def test_pad_batch(sft):
    a = {"input_ids": [5, 6, 7], "labels": [-100, 6, 7]}
    b = {"input_ids": [8, 9, 10, 11, 12], "labels": [-100, -100, 10, 11, 12]}
    out = sft.pad_batch([a, b], pad_token_id=0)
    assert set(out) == {"input_ids", "attention_mask", "labels"}
    assert all(v.dtype == torch.long for v in out.values())
    assert out["input_ids"].tolist() == [[5, 6, 7, 0, 0], [8, 9, 10, 11, 12]]
    assert out["attention_mask"].tolist() == [[1, 1, 1, 0, 0], [1, 1, 1, 1, 1]]
    assert out["labels"].tolist() == [[-100, 6, 7, -100, -100], [-100, -100, 10, 11, 12]]
    wide = sft.pad_batch([a, b], pad_token_id=99, multiple_of=8)
    assert wide["input_ids"].shape == (2, 8) and wide["input_ids"][0, 3:].tolist() == [99] * 5
    assert wide["labels"][1, 5:].tolist() == [-100] * 3 and wide["attention_mask"].sum().item() == 8


def test_loss_counts_only_assistant_tokens(sft):
    from transformers import Qwen2Config, Qwen2ForCausalLM

    torch.manual_seed(0)
    model = Qwen2ForCausalLM(Qwen2Config(vocab_size=8192, hidden_size=32, intermediate_size=64, num_hidden_layers=1,
                                         num_attention_heads=4, num_key_value_heads=2)).eval()
    tok = FakeTokenizer()
    batch = sft.pad_batch([sft.tokenize_chat(CHAT, tok), sft.tokenize_chat(MULTI, tok)], tok.pad_token_id)
    with torch.no_grad():
        out = model(**batch)
    logits = out.logits[:, :-1]
    target = batch["input_ids"][:, 1:]
    keep = batch["labels"][:, 1:] != -100
    manual = torch.nn.functional.cross_entropy(logits[keep], target[keep])
    assert keep.sum().item() == 10 + 6, "loss chỉ tính trên token của assistant: 10 token ở CHAT, 6 ở MULTI"
    torch.testing.assert_close(out.loss, manual, rtol=1e-5, atol=1e-5)


def test_pack_examples(sft):
    ex_ = [{"input_ids": list(range(10 * k, 10 * k + n)), "labels": [-100] + list(range(10 * k + 1, 10 * k + n))}
           for k, n in enumerate([4, 3, 5, 2, 9])]
    blocks = sft.pack_examples(ex_, block_size=8)
    assert [len(b["input_ids"]) for b in blocks] == [7, 7, 8], "nối tuần tự, không tách ví dụ, ví dụ dài bị cắt"
    assert blocks[0]["input_ids"] == [0, 1, 2, 3, 10, 11, 12]
    assert blocks[0]["position_ids"] == [0, 1, 2, 3, 0, 1, 2], "position_ids bắt đầu lại từ 0 ở mỗi ví dụ"
    assert blocks[1]["position_ids"] == [0, 1, 2, 3, 4, 0, 1]
    assert blocks[2]["input_ids"] == list(range(40, 48)) and blocks[2]["labels"][0] == -100
    assert all(len(b["labels"]) == len(b["input_ids"]) == len(b["position_ids"]) for b in blocks)
    assert sft.pack_examples(ex_[:1], block_size=4)[0]["input_ids"] == [0, 1, 2, 3]


def test_real_token_fraction(sft):
    assert sft.real_token_fraction([4, 4, 4, 4], batch_size=2) == pytest.approx(1.0)
    assert sft.real_token_fraction([10, 2, 3, 3], batch_size=2) == pytest.approx(18 / 26)
    assert sft.real_token_fraction([10, 2, 3], batch_size=2) == pytest.approx(15 / 23)
    assert sft.real_token_fraction([10, 2, 3, 3], batch_size=4) == pytest.approx(18 / 40)
