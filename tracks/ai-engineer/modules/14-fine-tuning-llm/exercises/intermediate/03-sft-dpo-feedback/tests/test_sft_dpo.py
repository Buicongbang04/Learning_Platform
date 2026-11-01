import json

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("sft_dpo.ipynb")


def test_to_chat(nb):
    chat = nb.to_chat("thầy dạy rất nhiệt tình .")
    assert [m["role"] for m in chat] == ["system", "user"]
    assert chat[0]["content"] == nb.SYSTEM and chat[1]["content"] == "thầy dạy rất nhiệt tình ."
    full = nb.to_chat("phòng học nóng .", "negative", "facility")
    assert full[:2] == nb.to_chat("phòng học nóng .")
    assert full[2] == {"role": "assistant", "content": '{"sentiment": "negative", "topic": "facility"}'}
    assert json.loads(nb.to_chat("x", "neutral", "others")[2]["content"]) == {"sentiment": "neutral", "topic": "others"}


@pytest.mark.parametrize("text,strict,expected", [
    ('{"sentiment": "positive", "topic": "lecturer"}', True, ("positive", "lecturer")),
    ('  {"topic": "facility", "sentiment": "negative"}\n', True, ("negative", "facility")),
    ('```json\n{"sentiment": "positive", "topic": "lecturer"}\n```', True, None),
    ('```json\n{"sentiment": "positive", "topic": "lecturer"}\n```', False, ("positive", "lecturer")),
    ('Kết quả: {"sentiment": "neutral", "topic": "others"} nhé', False, ("neutral", "others")),
    ('{"sentiment": "Positive", "topic": "lecturer"}', True, None),
    ('{"sentiment": "positive", "topic": "teacher"}', True, None),
    ('{"sentiment": "positive"}', True, None),
    ('{"sentiment": "positive", "topic": "lecturer", "note": "x"}', True, None),
    ('["positive", "lecturer"]', True, None),
    ('{"sentiment": "positive", "topic": "lecturer"', False, None),
    ("positive", False, None),
    ("", True, None),
])
def test_parse_output(nb, text, strict, expected):
    assert nb.parse_output(text, strict=strict) == expected


def test_parse_output_default_is_strict(nb):
    assert nb.parse_output('ok {"sentiment": "positive", "topic": "lecturer"}') is None


def test_macro_f1_matches_sklearn_and_counts_invalid_as_wrong(nb):
    from sklearn.metrics import f1_score

    y_true = ["negative", "neutral", "positive", "positive", "negative", "neutral", "positive"]
    y_pred = ["negative", "positive", "positive", None, "neutral", None, "positive"]
    expected = f1_score(y_true, ["<hỏng>" if p is None else p for p in y_pred],
                        labels=nb.SENTIMENTS, average="macro", zero_division=0)
    assert nb.macro_f1(y_true, y_pred, nb.SENTIMENTS) == pytest.approx(expected)
    assert nb.macro_f1(["a", "b"], ["a", "b"], ["a", "b", "c"]) == pytest.approx(2 / 3)
    assert nb.macro_f1(["a", "a"], [None, None], ["a"]) == 0.0


def test_preference_pairs(nb):
    sentences = ["a .", "b .", "c .", "d .", "e ."]
    gold = [("positive", "lecturer"), ("negative", "facility"), ("neutral", "others"), ("positive", "lecturer"),
            ("negative", "lecturer")]
    outputs = ['{"sentiment": "positive", "topic": "lecturer"}', '{"sentiment": "positive", "topic": "facility"}',
               "Câu này trung tính.", ' {"sentiment": "positive", "topic": "lecturer"} ',
               '```json\n{"sentiment": "negative", "topic": "lecturer"}\n```']
    pairs = nb.preference_pairs(sentences, gold, outputs)
    assert len(pairs) == 3, "chỉ câu model sai (đọc strict) mới thành cặp; bọc trong code fence là sai định dạng"
    assert pairs[2]["rejected"][0]["content"] == outputs[4]
    p = pairs[0]
    assert set(p) == {"prompt", "chosen", "rejected"}
    assert p["prompt"] == nb.to_chat("b .")
    assert p["chosen"] == [{"role": "assistant", "content": '{"sentiment": "negative", "topic": "facility"}'}]
    assert p["rejected"] == [{"role": "assistant", "content": outputs[1]}]
    assert pairs[1]["rejected"][0]["content"] == "Câu này trung tính."


class CharTokenizer:
    """Tokenizer giả mỗi ký tự một token, có chat template ChatML đơn giản."""

    eos_token = "\x03"
    eos_token_id = 3

    def __init__(self):
        self.pad_token = None
        self.pad_token_id = None
        self.padding_side = "right"

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False, **kwargs):
        text = "".join(f"<{m['role']}>{m['content']}\x03" for m in messages)
        return text + ("<assistant>" if add_generation_prompt else "")

    def _enc(self, text):
        if text == self.pad_token:
            return [self.pad_token_id]
        return [min(ord(c), 255) for c in text]

    def __call__(self, texts, return_tensors=None, padding=False, add_special_tokens=True):
        ids = [self._enc(t) for t in texts]
        width = max(map(len, ids))
        pad = self.pad_token_id if self.pad_token_id is not None else 0
        rows, mask = [], []
        for x in ids:
            n = width - len(x)
            if self.padding_side == "left":
                rows.append([pad] * n + x)
                mask.append([0] * n + [1] * len(x))
            else:
                rows.append(x + [pad] * n)
                mask.append([1] * len(x) + [0] * n)
        from transformers import BatchEncoding

        return BatchEncoding({"input_ids": torch.tensor(rows), "attention_mask": torch.tensor(mask)})

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)
        if key == "pad_token" and value == self.eos_token:
            object.__setattr__(self, "pad_token_id", self.eos_token_id)

    def batch_decode(self, rows, skip_special_tokens=True):
        return ["".join(chr(i) for i in r.tolist() if not (skip_special_tokens and i == 3)) for r in rows]


def test_generate_batch_equals_one_by_one(nb):
    from transformers import GenerationConfig, Qwen2Config, Qwen2ForCausalLM

    torch.manual_seed(0)
    model = Qwen2ForCausalLM(Qwen2Config(vocab_size=256, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                                         num_attention_heads=4, num_key_value_heads=2, eos_token_id=3,
                                         pad_token_id=3)).eval()
    model.generation_config = GenerationConfig(eos_token_id=None, pad_token_id=3)
    chats = [[{"role": "user", "content": "ngắn"}],
             [{"role": "user", "content": "một câu dài hơn hẳn câu kia"}],
             [{"role": "system", "content": "S"}, {"role": "user", "content": "vừa vừa"}]]
    tok = CharTokenizer()
    batched = nb.generate_batch(model, tok, chats, max_new_tokens=6, batch_size=3)
    single = [nb.generate_batch(model, CharTokenizer(), [c], max_new_tokens=6, batch_size=1)[0] for c in chats]
    assert len(batched) == 3 and all(isinstance(s, str) for s in batched)
    assert all(len(s) == 6 for s in single), "trả phần mới sinh, không lặp lại prompt"
    assert batched == single, "batch độ dài khác nhau phải cho cùng kết quả như sinh từng câu"
    again = nb.generate_batch(model, CharTokenizer(), chats, max_new_tokens=6, batch_size=2)
    assert again == single, "nhiều batch giữ đúng thứ tự"
