import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def c():
    return ex.module("context.py")


def chars(text: str) -> int:
    return len(text)


# ---------- truncate_middle ----------


def test_truncate_short_text_unchanged(c):
    assert c.truncate_middle("ngắn", 10, count=chars) == "ngắn"
    text = "x" * 50
    assert c.truncate_middle(text, 50, count=chars) is text or c.truncate_middle(text, 50, count=chars) == text


def test_truncate_keeps_head_and_tail(c):
    text = "ĐẦU" + "-" * 200 + "CUỐI"
    out = c.truncate_middle(text, 60, count=chars)
    assert len(out) <= 60
    assert out.startswith("ĐẦU") and out.endswith("CUỐI")
    k = out.index("\n...[")
    assert out == text[:k] + c._marker(len(text) - 2 * k) + text[len(text) - k:], "đúng k ký tự đầu, k ký tự cuối"


def test_truncate_is_maximal(c):
    text = "".join(chr(ord("a") + i % 26) for i in range(1000))
    for budget in (40, 41, 100, 333):
        out = c.truncate_middle(text, budget, count=chars)
        k = out.index("\n...[")
        assert len(out) <= budget
        bigger = text[:k + 1] + c._marker(len(text) - 2 * (k + 1)) + text[len(text) - k - 1:]
        assert len(bigger) > budget, f"budget={budget}: giữ thêm 1 ký tự mỗi đầu vẫn vừa, chưa phải k lớn nhất"


def test_truncate_with_word_counter(c):
    text = " ".join(f"w{i}" for i in range(500))
    words = lambda s: len(s.split())
    out = c.truncate_middle(text, 30, count=words)
    assert words(out) <= 30 and out.startswith("w0 ") and out.endswith(" w499")


def test_truncate_budget_too_small(c):
    with pytest.raises(c.ContextOverflowError):
        c.truncate_middle("y" * 500, 10, count=chars)


# ---------- compact_history ----------


def history(n_obs=4, size=200):
    msgs = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "TASK"}]
    for i in range(n_obs):
        msgs.append({"role": "assistant", "content": f"Action: tool{i}"})
        msgs.append({"role": "user", "content": "Observation: " + f"[{i}]" + "z" * size})
    return msgs


def test_compact_keeps_last_observations(c):
    msgs = history()
    out = c.compact_history(msgs, keep_last=2, stub_chars=10)
    assert len(out) == len(msgs)
    assert out[-1] == msgs[-1] and out[-3] == msgs[-3], "2 observation cuối giữ nguyên"
    body = msgs[3]["content"][len("Observation: "):]
    assert out[3]["content"] == f"Observation: [đã rút gọn, {len(body)} ký tự] {body[:10]}..."
    assert out[5]["content"].startswith("Observation: [đã rút gọn, 203 ký tự] [1]zzzzzzz")
    assert [m for i, m in enumerate(out) if i not in (3, 5)] == [m for i, m in enumerate(msgs) if i not in (3, 5)]


def test_compact_short_and_non_observation_untouched(c):
    msgs = history(n_obs=3, size=5)
    msgs.append({"role": "user", "content": "Lỗi định dạng: " + "q" * 300})
    out = c.compact_history(msgs, keep_last=1, stub_chars=60)
    assert out == msgs, "observation ngắn hơn stub_chars và message không phải observation giữ nguyên"


def test_compact_keep_zero_and_no_mutation(c):
    msgs = history(n_obs=2)
    snapshot = [dict(m) for m in msgs]
    out = c.compact_history(msgs, keep_last=0, stub_chars=5)
    assert all("[đã rút gọn" in m["content"] for m in out if m["content"].startswith("Observation: "))
    assert msgs == snapshot, "không sửa đầu vào"
    assert out[3] is not msgs[3]


# ---------- fit_messages ----------


def convo(n):
    msgs = [{"role": "system", "content": "S" * 40}, {"role": "user", "content": "T" * 20}]
    for i in range(n):
        msgs.append({"role": "assistant" if i % 2 == 0 else "user", "content": f"{i:02d}" + "m" * 18})
    return msgs


def test_fit_no_change_when_within_budget(c):
    msgs = convo(4)
    assert c.messages_tokens(convo(0), count=chars) == 40 + 20 + 2 * c.MSG_OVERHEAD
    total = c.messages_tokens(msgs, count=chars)
    out = c.fit_messages(msgs, total, count=chars)
    assert out == msgs and out is not msgs


def test_fit_pins_system_and_task_keeps_longest_suffix(c):
    msgs = convo(10)
    budget = 220
    out = c.fit_messages(msgs, budget, count=chars, keep_last=2)
    assert out[0] == msgs[0] and out[1] == msgs[1], "system và task luôn còn"
    assert c.messages_tokens(out, count=chars) <= budget
    note = out[2]
    kept = out[3:]
    assert kept == msgs[len(msgs) - len(kept):], "phần giữ lại là đoạn đuôi liên tục"
    assert note == c.dropped_note(10 - len(kept))
    longer = [*msgs[:2], c.dropped_note(10 - len(kept) - 1), *msgs[len(msgs) - len(kept) - 1:]]
    assert c.messages_tokens(longer, count=chars) > budget, "chưa giữ được đoạn đuôi dài nhất"
    assert len(kept) == 4


def test_fit_overflow(c):
    msgs = convo(6)
    with pytest.raises(c.ContextOverflowError):
        c.fit_messages(msgs, 150, count=chars, keep_last=4)
    out = c.fit_messages(msgs, 150, count=chars, keep_last=1)
    assert len(out) == 4 and out[-1] == msgs[-1]


def test_fit_does_not_mutate(c):
    msgs = convo(8)
    snapshot = [dict(m) for m in msgs]
    out = c.fit_messages(msgs, 200, count=chars, keep_last=1)
    out[0]["content"] = "đổi"
    assert msgs == snapshot
