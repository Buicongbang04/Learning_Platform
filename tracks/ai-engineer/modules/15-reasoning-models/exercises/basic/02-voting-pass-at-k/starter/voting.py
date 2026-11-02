"""Gộp nhiều lời giải: majority vote, weighted vote, best-of-N, và các thước đo maj@k, pass@k.

Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

from collections.abc import Sequence


def majority_vote(answers: Sequence[str | None]) -> str | None:
    """Đáp số xuất hiện nhiều nhất (bỏ None). Hoà: đáp số xuất hiện sớm nhất trong danh sách. Không có gì: None."""
    # TODO
    raise NotImplementedError


def weighted_vote(answers: Sequence[str | None], weights: Sequence[float]) -> str | None:
    """Đáp số có tổng trọng số lớn nhất (bỏ None). Hoà: đáp số xuất hiện sớm nhất. Không có gì: None."""
    # TODO
    raise NotImplementedError


def best_of_n(answers: Sequence[str | None], scores: Sequence[float]) -> str | None:
    """Đáp số của lời giải có điểm verifier cao nhất. Hoà: lời giải đứng trước."""
    # TODO
    raise NotImplementedError


def pass_at_k(n: int, c: int, k: int) -> float:
    """Ước lượng không chệch của P(ít nhất một trong k lời giải đúng) từ n lời giải có c lời giải đúng."""
    # TODO
    raise NotImplementedError


def maj_at_k(samples: Sequence[Sequence[str | None]], golds: Sequence[str], k: int) -> float:
    """Độ chính xác của majority vote trên k lời giải, trung bình theo các khối k liên tiếp rồi theo câu hỏi."""
    # TODO
    raise NotImplementedError


def coverage_at_k(samples: Sequence[Sequence[str | None]], golds: Sequence[str], k: int) -> float:
    """Trung bình pass@k theo câu hỏi."""
    # TODO
    raise NotImplementedError
