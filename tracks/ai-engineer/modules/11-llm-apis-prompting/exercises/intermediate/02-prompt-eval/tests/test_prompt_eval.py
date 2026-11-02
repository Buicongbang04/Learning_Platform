import numpy as np
import pytest
from sklearn.metrics import f1_score

from testkit import Exercise

ex = Exercise(__file__)

LABELS = ["negative", "neutral", "positive"]
EXAMPLES = [("phòng học nóng .", "negative"), ("không ý kiến .", "neutral"), ("thầy dạy hay .", "positive"),
            ("thiếu tài liệu .", "negative")]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("prompt_eval.ipynb")


def test_zero_shot_and_cot_and_json(nb):
    assert nb.LABELS == LABELS
    assert nb.VARIANTS == ["zero_shot", "few_shot", "cot", "json_schema"]
    assert nb.SCHEMA["properties"]["label"]["enum"] == LABELS
    assert nb.NUM_PREDICT == {"zero_shot": 8, "few_shot": 8, "cot": 160, "json_schema": 32}
    for variant, tail in [("zero_shot", nb.ONE_WORD), ("cot", nb.COT), ("json_schema", nb.JSON_INSTR)]:
        msgs = nb.build_messages(variant, "giảng viên dạy hay .", EXAMPLES)
        assert msgs == [{"role": "system", "content": nb.TASK + tail},
                        {"role": "user", "content": "Phản hồi: giảng viên dạy hay ."}], variant


def test_few_shot_turns(nb):
    msgs = nb.build_messages("few_shot", "wifi yếu .", EXAMPLES)
    assert msgs[0] == {"role": "system", "content": nb.TASK + nb.ONE_WORD}
    assert [m["role"] for m in msgs] == ["system"] + ["user", "assistant"] * 4 + ["user"]
    assert msgs[1] == {"role": "user", "content": "Phản hồi: phòng học nóng ."}
    assert msgs[2] == {"role": "assistant", "content": "negative"}
    assert [m["content"] for m in msgs[2:9:2]] == ["negative", "neutral", "positive", "negative"], "giữ thứ tự ví dụ"
    assert msgs[-1] == {"role": "user", "content": "Phản hồi: wifi yếu ."}
    assert nb.build_messages("few_shot", "x", []) == nb.build_messages("zero_shot", "x", [])


def test_unknown_variant(nb):
    with pytest.raises(ValueError):
        nb.build_messages("self_consistency", "x", EXAMPLES)


# ---------- parse_label ----------

@pytest.mark.parametrize("reply, expected", [
    ("negative", "negative"), ("Positive.", "positive"), ("  neutral\n", "neutral"),
    ("Nhãn: NEGATIVE", "negative"), ("neutral, neutral", "neutral"),
    ("positive hoặc negative", None), ("tích cực", None), ("", None), ("negatively", None),
])
def test_parse_one_word(nb, reply, expected):
    assert nb.parse_label("zero_shot", reply) == expected
    assert nb.parse_label("few_shot", reply) == expected


@pytest.mark.parametrize("reply, expected", [
    ("Ý chính: sinh viên khen, không phải negative.\nNhãn: positive", "positive"),
    ("Ý chính: chê phòng học.\nNhãn: `negative`", "negative"),
    ("Ý chính: trung lập.\n**Nhãn:** neutral", "neutral"),
    ("Ý chính: x. nhãn: positive\nNHÃN : Negative", "negative"),
    ("Ý chính: phản hồi này là positive.", None),
    ("Nhãn: tích cực", None),
])
def test_parse_cot(nb, reply, expected):
    assert nb.parse_label("cot", reply) == expected


@pytest.mark.parametrize("reply, expected", [
    ('{"label": "neutral"}', "neutral"), ('  {"label": "positive"}\n', "positive"),
    ('{"label": "tích cực"}', None), ('{"nhan": "neutral"}', None), ('["neutral"]', None),
    ('{"label": "neutral"', None), ("neutral", None), ('{"label": null}', None),
])
def test_parse_json(nb, reply, expected):
    assert nb.parse_label("json_schema", reply) == expected


# ---------- macro_f1 ----------

def test_macro_f1_hand(nb):
    y = ["negative", "negative", "neutral", "positive", "positive", "neutral"]
    p = ["negative", "positive", None, "positive", "positive", "neutral"]
    # negative: tp1 fp0 fn1 -> 2/3; neutral: tp1 fp0 fn1 -> 2/3; positive: tp2 fp1 fn0 -> 4/5
    assert nb.macro_f1(y, p) == pytest.approx((2 / 3 + 2 / 3 + 0.8) / 3, abs=1e-12)
    assert nb.macro_f1(y, y) == 1.0
    assert nb.macro_f1(y, [None] * 6) == 0.0
    assert isinstance(nb.macro_f1(y, p), float)


def test_macro_f1_matches_sklearn(nb):
    rng = np.random.default_rng(1)
    choices = LABELS + [None]
    for _ in range(30):
        n = int(rng.integers(5, 60))
        y = [LABELS[i] for i in rng.integers(0, 3, n)]
        p = [choices[i] for i in rng.integers(0, 4, n)]
        ref = f1_score(y, ["none" if v is None else v for v in p], labels=LABELS, average="macro", zero_division=0)
        assert nb.macro_f1(y, p) == pytest.approx(ref, abs=1e-12)


# ---------- paired_bootstrap ----------

def reference_bootstrap(nb, y, a, b, n_boot, seed):
    y, a, b = (np.array(v, dtype=object) for v in (y, a, b))
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        diffs.append(nb.macro_f1(list(y[idx]), list(b[idx])) - nb.macro_f1(list(y[idx]), list(a[idx])))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return nb.macro_f1(list(y), list(b)) - nb.macro_f1(list(y), list(a)), lo, hi


def synthetic(seed, n=90, acc_a=0.7, acc_b=0.8):
    rng = np.random.default_rng(seed)
    y = [LABELS[i] for i in rng.integers(0, 3, n)]

    def noisy(acc):
        return [t if rng.random() < acc else LABELS[(LABELS.index(t) + 1) % 3] for t in y]

    return y, noisy(acc_a), noisy(acc_b)


def test_bootstrap_exact_procedure(nb):
    y, a, b = synthetic(0)
    got = nb.paired_bootstrap(y, a, b, n_boot=300, seed=7)
    assert all(isinstance(v, float) for v in got)
    assert got == pytest.approx(reference_bootstrap(nb, y, a, b, 300, 7), abs=1e-12)
    assert got[1] <= got[0] <= got[2]


def test_bootstrap_is_paired_and_seeded(nb):
    y, a, _ = synthetic(1)
    assert nb.paired_bootstrap(y, a, a, n_boot=200, seed=0) == (0.0, 0.0, 0.0), "cùng dự đoán: hiệu luôn 0 nếu theo cặp"
    y, a, b = synthetic(2)
    assert nb.paired_bootstrap(y, a, b, n_boot=200, seed=3) == nb.paired_bootstrap(y, a, b, n_boot=200, seed=3)
    d_ab = nb.paired_bootstrap(y, a, b, n_boot=200, seed=3)
    d_ba = nb.paired_bootstrap(y, b, a, n_boot=200, seed=3)
    assert d_ab[0] == pytest.approx(-d_ba[0]) and d_ab[1] == pytest.approx(-d_ba[2]), "hiệu là B trừ A"


def test_bootstrap_default_args(nb):
    y, a, b = synthetic(4, n=40)
    assert nb.paired_bootstrap(y, a, b) == pytest.approx(reference_bootstrap(nb, y, a, b, 2000, 0), abs=1e-12)
