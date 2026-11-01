"""Đo độ khớp của LLM judge với nhãn người và thiên vị vị trí (lời giải)."""

from __future__ import annotations

import math
from collections import Counter

VERDICTS = ("first", "second", "tie")


def cohen_kappa(a, b) -> float:
    a, b = list(a), list(b)
    if len(a) != len(b) or not a:
        raise ValueError("hai dãy nhãn phải cùng độ dài, không rỗng")
    n = len(a)
    p_o = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    p_e = sum(ca[label] * cb[label] for label in ca) / (n * n)
    if p_e == 1:
        return math.nan
    return (p_o - p_e) / (1 - p_e)


def calibration_report(judge, human) -> dict:
    judge, human = list(judge), list(human)
    if len(judge) != len(human):
        raise ValueError("judge và human phải cùng độ dài")
    pairs = [(j, h) for j, h in zip(judge, human) if j is not None]
    if not pairs:
        raise ValueError("không có verdict nào đọc được")
    js = [bool(j) for j, _ in pairs]
    hs = [bool(h) for _, h in pairs]
    neg = [j for j, h in zip(js, hs) if not h]
    pos = [j for j, h in zip(js, hs) if h]
    return {
        "n": len(pairs),
        "unparsed": len(judge) - len(pairs),
        "accuracy": sum(j == h for j, h in zip(js, hs)) / len(pairs),
        "kappa": cohen_kappa(js, hs),
        "false_pass": sum(neg) / len(neg) if neg else math.nan,
        "false_fail": sum(not j for j in pos) / len(pos) if pos else math.nan,
        "judge_pass_rate": sum(js) / len(js),
        "human_pass_rate": sum(hs) / len(hs),
    }


def resolve_swap(v_ab: str, v_ba: str) -> str:
    if v_ab not in VERDICTS or v_ba not in VERDICTS:
        raise ValueError(f"verdict phải thuộc {VERDICTS}")
    w1 = {"first": "A", "second": "B", "tie": "tie"}[v_ab]
    w2 = {"first": "B", "second": "A", "tie": "tie"}[v_ba]
    return w1 if w1 == w2 else "inconsistent"


def pairwise_summary(pairs) -> dict:
    pairs = list(pairs)
    if not pairs:
        raise ValueError("không có cặp nào")
    outcomes = Counter(resolve_swap(v_ab, v_ba) for v_ab, v_ba in pairs)
    n = len(pairs)
    decisive = [v for pair in pairs for v in pair if v != "tie"]
    return {
        "n": n,
        "A": outcomes["A"],
        "B": outcomes["B"],
        "tie": outcomes["tie"],
        "inconsistent": outcomes["inconsistent"],
        "consistency": (n - outcomes["inconsistent"]) / n,
        "win_rate_A": (outcomes["A"] + 0.5 * (outcomes["tie"] + outcomes["inconsistent"])) / n,
        "first_rate": sum(v == "first" for v in decisive) / len(decisive) if decisive else math.nan,
    }
