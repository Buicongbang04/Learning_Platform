"""WER và CER cho tiếng Việt: chuẩn hoá, đếm S/D/I bằng quy hoạch động, tổng hợp mức corpus."""

from __future__ import annotations

import unicodedata


def normalize_vi(text: str) -> str:
    """NFC, chữ thường, bỏ dấu câu và ký hiệu (giữ dấu thanh), gộp khoảng trắng."""
    text = unicodedata.normalize("NFC", text).lower()
    kept = [" " if unicodedata.category(ch)[0] in "PSZ" else ch for ch in text]
    return " ".join("".join(kept).split())


def edit_counts(ref: list[str], hyp: list[str]) -> dict[str, int]:
    """Số substitution, deletion, insertion của một alignment có tổng lỗi nhỏ nhất, và N = len(ref)."""
    n, m = len(ref), len(hyp)
    cost = [[(0, 0, 0, 0)] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = (i, 0, i, 0)
    for j in range(1, m + 1):
        cost[0][j] = (j, 0, 0, j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                cost[i][j] = cost[i - 1][j - 1]
                continue
            t, s, d, ins = cost[i - 1][j - 1]
            sub = (t + 1, s + 1, d, ins)
            t, s, d, ins = cost[i - 1][j]
            dele = (t + 1, s, d + 1, ins)
            t, s, d, ins = cost[i][j - 1]
            add = (t + 1, s, d, ins + 1)
            cost[i][j] = min(sub, dele, add)
    total, s, d, ins = cost[n][m]
    return {"S": s, "D": d, "I": ins, "N": n}


def _corpus_rate(refs: list[str], hyps: list[str], split) -> float:
    if len(refs) != len(hyps):
        raise ValueError("số câu tham chiếu và số câu nhận dạng khác nhau")
    errors = words = 0
    for ref, hyp in zip(refs, hyps):
        c = edit_counts(split(normalize_vi(ref)), split(normalize_vi(hyp)))
        errors += c["S"] + c["D"] + c["I"]
        words += c["N"]
    if words == 0:
        raise ValueError("tham chiếu rỗng: WER/CER không xác định")
    return errors / words


def wer(refs: list[str], hyps: list[str]) -> float:
    """WER mức corpus: tổng S + D + I trên mọi câu chia tổng số từ tham chiếu (sau normalize_vi)."""
    return _corpus_rate(refs, hyps, str.split)


def cer(refs: list[str], hyps: list[str]) -> float:
    """CER mức corpus trên ký tự của chuỗi đã normalize_vi, tính cả khoảng trắng."""
    return _corpus_rate(refs, hyps, list)
