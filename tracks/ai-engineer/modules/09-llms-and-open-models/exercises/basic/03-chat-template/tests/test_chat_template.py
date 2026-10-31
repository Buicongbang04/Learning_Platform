import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Chuỗi mong đợi sinh bằng tokenizer thật: AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")
# .apply_chat_template(..., tokenize=False), và template Jinja của Meta-Llama-3-8B-Instruct render bằng jinja2.
SYS = "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n"

LEGAL = [
    {"role": "system", "content": "Bạn là trợ lý pháp luật."},
    {"role": "user", "content": "Phạt nồng độ cồn bao nhiêu?"},
    {"role": "assistant", "content": "Tuỳ mức vi phạm."},
    {"role": "user", "content": "Xe máy thì sao?"},
]
TOOLS = [
    {"role": "user", "content": "Thời tiết Hà Nội?"},
    {"role": "assistant", "content": "Để tôi tra."},
    {"role": "tool", "content": '{"temp": 30}'},
    {"role": "tool", "content": '{"rain": false}'},
    {"role": "user", "content": "Cảm ơn"},
]


@pytest.fixture(scope="module")
def ct():
    return ex.module("chat_template.py")


# ---------- Qwen2.5 / ChatML ----------


def test_qwen_default_system(ct):
    msgs = [{"role": "user", "content": "Xin chào"}]
    assert ct.render_qwen(msgs) == SYS + "<|im_start|>user\nXin chào<|im_end|>\n<|im_start|>assistant\n"
    assert ct.render_qwen(msgs, add_generation_prompt=False) == SYS + "<|im_start|>user\nXin chào<|im_end|>\n"


def test_qwen_own_system_replaces_default(ct):
    assert ct.render_qwen(LEGAL) == (
        "<|im_start|>system\nBạn là trợ lý pháp luật.<|im_end|>\n<|im_start|>user\nPhạt nồng độ cồn bao nhiêu?"
        "<|im_end|>\n<|im_start|>assistant\nTuỳ mức vi phạm.<|im_end|>\n<|im_start|>user\nXe máy thì sao?"
        "<|im_end|>\n<|im_start|>assistant\n"
    )


def test_qwen_keeps_whitespace_and_mid_system(ct):
    assert ct.render_qwen([{"role": "user", "content": "  có khoảng trắng  "}]) == (
        SYS + "<|im_start|>user\n  có khoảng trắng  <|im_end|>\n<|im_start|>assistant\n"
    )
    mid = [{"role": "user", "content": "a"}, {"role": "system", "content": "b"}]
    assert ct.render_qwen(mid, add_generation_prompt=False) == (
        SYS + "<|im_start|>user\na<|im_end|>\n<|im_start|>system\nb<|im_end|>\n"
    )


def test_qwen_groups_consecutive_tool_messages(ct):
    assert ct.render_qwen(TOOLS) == (
        SYS + "<|im_start|>user\nThời tiết Hà Nội?<|im_end|>\n<|im_start|>assistant\nĐể tôi tra.<|im_end|>\n"
        '<|im_start|>user\n<tool_response>\n{"temp": 30}\n</tool_response>\n<tool_response>\n{"rain": false}\n'
        "</tool_response><|im_end|>\n<|im_start|>user\nCảm ơn<|im_end|>\n<|im_start|>assistant\n"
    )
    single = [{"role": "user", "content": "q"}, {"role": "tool", "content": "42"}]
    assert ct.render_qwen(single, add_generation_prompt=False) == (
        SYS + "<|im_start|>user\nq<|im_end|>\n<|im_start|>user\n<tool_response>\n42\n</tool_response><|im_end|>\n"
    )


# ---------- Llama 3 ----------


def test_llama3(ct):
    msgs = [
        {"role": "system", "content": "Bạn là trợ lý pháp luật."},
        {"role": "user", "content": "  Phạt nồng độ cồn bao nhiêu?\n"},
        {"role": "assistant", "content": "Tuỳ mức vi phạm."},
    ]
    body = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nBạn là trợ lý pháp luật.<|eot_id|>"
        "<|start_header_id|>user<|end_header_id|>\n\nPhạt nồng độ cồn bao nhiêu?<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\nTuỳ mức vi phạm.<|eot_id|>"
    )
    assert ct.render_llama3(msgs, add_generation_prompt=False) == body
    assert ct.render_llama3(msgs) == body + "<|start_header_id|>assistant<|end_header_id|>\n\n"
    assert ct.render_llama3([]) == "<|start_header_id|>assistant<|end_header_id|>\n\n"
    assert "You are" not in ct.render_llama3([{"role": "user", "content": "hi"}]), "Llama 3 không có system mặc định"


# ---------- parse ----------


def test_parse_roundtrip(ct):
    text = ct.render_qwen(LEGAL)
    assert ct.parse_chatml(text) == LEGAL, "khối generation prompt chưa đóng bị bỏ qua"
    multi = [{"role": "user", "content": "dòng 1\ndòng 2\n"}, {"role": "assistant", "content": "ok"}]
    assert ct.parse_chatml(ct.render_qwen(multi, add_generation_prompt=False))[1:] == multi
    assert ct.parse_chatml("") == []


# ---------- fit_history ----------


def words(text: str) -> int:
    return len(text.split())


def conv(*pairs):
    return [{"role": r, "content": c} for r, c in pairs]


HIST = conv(
    ("system", "s s"),                    # 2 + 4 = 6
    ("user", "u1 u1 u1"),                 # 7
    ("assistant", "a1 a1 a1 a1"),         # 8
    ("user", "u2"),                       # 5
    ("assistant", "a2 a2"),               # 6
    ("user", "u3 u3 u3"),                 # 7
)


def test_fit_history_keeps_all_when_budget_allows(ct):
    out = ct.fit_history(HIST, 39, words)
    assert out == HIST and out is not HIST
    assert out[0] is HIST[0]


def test_fit_history_drops_oldest_and_keeps_system(ct):
    # system 6 + u3 7 + a2 6 + u2 5 = 24; thêm a1 (8) là 32 > 30
    assert ct.fit_history(HIST, 30, words) == [HIST[0], HIST[3], HIST[4], HIST[5]]


def test_fit_history_window_starts_with_user(ct):
    # system 6 + u3 7 + a2 6 = 19 <= 22, thêm u2 (5) là 24 > 22: đoạn [a2, u3] bắt đầu bằng assistant, bỏ a2
    assert ct.fit_history(HIST, 22, words) == [HIST[0], HIST[5]]


def test_fit_history_contiguous_and_per_message(ct):
    h = conv(("user", "x " * 10), ("assistant", "y"), ("user", "z " * 20), ("assistant", "w"), ("user", "q"))
    # không system; q 5, w 5, z 24: 34 > 20 nên dừng, không nhảy cóc lấy y
    assert ct.fit_history(h, 20, words) == [h[4]]
    assert ct.fit_history(h, 20, words, per_message=0) == [h[4]], "đoạn [w, q] bắt đầu bằng assistant"
    assert ct.fit_history(h, 22, words, per_message=0) == [h[2], h[3], h[4]]


def test_fit_history_too_small_raises(ct):
    with pytest.raises(ValueError):
        ct.fit_history(HIST, 12, words)
    assert ct.fit_history(HIST, 13, words) == [HIST[0], HIST[5]]
