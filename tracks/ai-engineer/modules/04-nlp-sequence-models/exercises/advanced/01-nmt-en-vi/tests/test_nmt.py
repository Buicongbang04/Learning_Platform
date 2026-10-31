import html
import math
import re

import pytest
import torch
from testkit import Exercise

ex = Exercise(__file__)
BOS, EOS = 1, 2


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("nmt.ipynb")


def table_model(probs: dict[tuple, dict[int, float]], V: int = 6):
    """step_fn từ bảng xác suất theo tiền tố; tiền tố không có trong bảng thì đều nhau. Kiểm không mở rộng câu đã xong."""
    calls = []

    def step_fn(prefixes):
        out = torch.full((len(prefixes), V), -1e9)
        for i, p in enumerate(prefixes):
            assert p[0] == BOS and EOS not in p, "không được mở rộng tiền tố đã có <eos>"
            calls.append(tuple(p))
            dist = probs.get(tuple(p), {t: 1 / V for t in range(V)})
            for t, q in dist.items():
                out[i, t] = math.log(q)
        return out

    return step_fn, calls


def test_greedy_trap(nb):
    # greedy chọn 3 (0.6) rồi chỉ còn các lựa chọn 0.3; beam thấy 4 (0.4) rồi 5 (0.9)
    probs = {
        (BOS,): {3: 0.6, 4: 0.4},
        (BOS, 3): {5: 0.3, 0: 0.3, EOS: 0.3, 4: 0.1},
        (BOS, 4): {5: 0.9, 0: 0.1},
        (BOS, 3, 5): {EOS: 1.0}, (BOS, 3, 0): {EOS: 1.0},
        (BOS, 4, 5): {EOS: 1.0}, (BOS, 4, 0): {EOS: 1.0},
    }
    fn, _ = table_model(probs)
    assert nb.beam_search(fn, BOS, EOS, beam_size=1, max_len=5, alpha=0.0) == [3, 5]
    fn, _ = table_model(probs)
    assert nb.beam_search(fn, BOS, EOS, beam_size=2, max_len=5, alpha=0.0) == [4, 5]


def test_length_penalty(nb):
    # câu ngắn: <eos> ngay (0.5, log -0.693, L = 1); câu dài: 3, 4, <eos> (0.5 * 0.95 * 0.95, log -0.796, L = 3)
    probs = {(BOS,): {EOS: 0.5, 3: 0.5}, (BOS, 3): {4: 0.95, 0: 0.05}, (BOS, 3, 4): {EOS: 0.95, 0: 0.05}}
    fn, _ = table_model(probs)
    assert nb.beam_search(fn, BOS, EOS, beam_size=2, max_len=6, alpha=0.0) == []
    fn, _ = table_model(probs)
    assert nb.beam_search(fn, BOS, EOS, beam_size=2, max_len=6, alpha=1.0) == [3, 4], \
        "chuẩn hoá chia cho ((5 + L) / 6) ** alpha"
    fn, _ = table_model(probs)
    # alpha = 0.45: tính L kể cả <eos> thì câu ngắn còn thắng (L không kể <eos> thì câu dài thắng)
    assert nb.beam_search(fn, BOS, EOS, beam_size=2, max_len=6, alpha=0.45) == [], "L tính cả <eos>"


def test_max_len_without_eos(nb):
    probs = {(BOS,): {3: 0.9, 4: 0.1}, (BOS, 3): {3: 0.9, 4: 0.1}, (BOS, 3, 3): {3: 0.9, 4: 0.1}}
    fn, _ = table_model(probs)
    out = nb.beam_search(fn, BOS, EOS, beam_size=2, max_len=3, alpha=0.6)
    assert out == [3, 3, 3], "không câu nào xong: trả beam sống tốt nhất, dài đúng max_len"


def test_beam1_equals_greedy_on_random_model(nb):
    g = torch.Generator().manual_seed(0)
    T = torch.log_softmax(torch.randn(8, 8, generator=g) * 2, dim=-1)   # log p(token | token trước)
    for start in range(3, 8):                                            # bước đầu dùng dòng `start` thay cho dòng BOS
        def fn(prefixes, s=start):
            return torch.stack([T[s] if len(p) == 1 else T[p[-1]] for p in prefixes])

        seq, last = [], int(T[start].argmax())
        while last != EOS and len(seq) < 10:
            seq.append(last)
            last = int(T[last].argmax())
        assert nb.beam_search(fn, BOS, EOS, beam_size=1, max_len=10, alpha=0.6) == seq


def test_beam_never_worse_than_greedy(nb):
    g = torch.Generator().manual_seed(1)
    T = torch.log_softmax(torch.randn(8, 8, generator=g) * 1.5, dim=-1)

    def fn(prefixes):
        return torch.stack([T[p[-1]] for p in prefixes])

    def logp(seq):
        prev, total = BOS, 0.0
        for t in seq + [EOS]:
            total += float(T[prev, t])
            prev = t
        return total

    greedy = nb.beam_search(fn, BOS, EOS, beam_size=1, max_len=12, alpha=0.0)
    beam = nb.beam_search(fn, BOS, EOS, beam_size=4, max_len=12, alpha=0.0)
    assert logp(beam) >= logp(greedy) - 1e-6


# ---------- Bản dịch thật: cần chạy notebook và tải IWSLT'15 ----------

def test_hypotheses_bleu():
    import sacrebleu

    hyp_path = ex.path("tst2013.hyp.vi")
    root = ex.dataset("iwslt15-en-vi")
    refs = [html.unescape(s) for s in (root / "tst2013.vi").read_text(encoding="utf-8").splitlines()]
    hyps = hyp_path.read_text(encoding="utf-8").splitlines()
    assert len(hyps) == len(refs) == 1268, "mỗi câu test đúng một dòng bản dịch"
    bleu = sacrebleu.corpus_bleu(hyps, [refs], tokenize="none").score
    # Bản tham chiếu (Luong, GRU 512, 8 epoch, beam 5): 11.6
    assert bleu >= 8.0, f"BLEU tst2013 = {bleu:.2f}"


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo portfolio: ít nhất 600 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng (ablation)"
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc)
    assert images, "chèn hình (đường cong học, attention heatmap)"
    for img in images:
        if not img.startswith("http"):
            assert (ex.path("REPORT.md").parent / img).exists(), f"không thấy tệp hình {img}"
