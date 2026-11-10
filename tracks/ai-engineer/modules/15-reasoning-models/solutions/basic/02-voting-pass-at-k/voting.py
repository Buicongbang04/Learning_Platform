"""Gộp nhiều lời giải: majority vote, weighted vote, best-of-N, và các thước đo maj@k, pass@k.

Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

from collections.abc import Sequence


def _check_lengths(a: Sequence, b: Sequence) -> None:
    if len(a) != len(b):
        raise ValueError(f"độ dài khác nhau: {len(a)} và {len(b)}")


def weighted_vote(answers: Sequence[str | None], weights: Sequence[float]) -> str | None:
    """Đáp số có tổng trọng số lớn nhất (bỏ None). Hoà: đáp số xuất hiện sớm nhất. Không có gì: None."""
    _check_lengths(answers, weights)
    totals: dict[str, float] = {}
    for answer, weight in zip(answers, weights):
        if answer is not None:
            totals[answer] = totals.get(answer, 0.0) + weight
    if not totals:
        return None
    best = max(totals.values())
    return next(a for a, total in totals.items() if total == best)


def majority_vote(answers: Sequence[str | None]) -> str | None:
    """Đáp số xuất hiện nhiều nhất (bỏ None). Hoà: đáp số xuất hiện sớm nhất trong danh sách. Không có gì: None."""
    return weighted_vote(answers, [1.0] * len(answers))


def best_of_n(answers: Sequence[str | None], scores: Sequence[float]) -> str | None:
    """Đáp số của lời giải có điểm verifier cao nhất. Hoà: lời giải đứng trước."""
    _check_lengths(answers, scores)
    if not answers:
        return None
    best = max(range(len(scores)), key=lambda i: (scores[i], -i))
    return answers[best]


def pass_at_k(n: int, c: int, k: int) -> float:
    """Ước lượng không chệch của P(ít nhất một trong k lời giải đúng) từ n lời giải có c lời giải đúng."""
    if not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError(f"cần 0 <= c <= n và 1 <= k <= n, nhận n={n}, c={c}, k={k}")
    if n - c < k:
        return 1.0
    fail = 1.0
    for i in range(n - c + 1, n + 1):
        fail *= 1.0 - k / i
    return 1.0 - fail


def maj_at_k(samples: Sequence[Sequence[str | None]], golds: Sequence[str], k: int) -> float:
    """Độ chính xác của majority vote trên k lời giải, trung bình theo các khối k liên tiếp rồi theo câu hỏi."""
    _check_lengths(samples, golds)
    per_question = []
    for answers, gold in zip(samples, golds):
        blocks = len(answers) // k
        if k < 1 or blocks == 0:
            raise ValueError(f"cần 1 <= k <= số lời giải ({len(answers)}), nhận k={k}")
        hits = sum(majority_vote(answers[b * k:(b + 1) * k]) == gold for b in range(blocks))
        per_question.append(hits / blocks)
    return sum(per_question) / len(per_question)


def coverage_at_k(samples: Sequence[Sequence[str | None]], golds: Sequence[str], k: int) -> float:
    """Trung bình pass@k theo câu hỏi."""
    _check_lengths(samples, golds)
    scores = [pass_at_k(len(answers), sum(a == gold for a in answers), k) for answers, gold in zip(samples, golds)]
    return sum(scores) / len(scores)
