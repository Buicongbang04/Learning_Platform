"""Ma trận quyết định có trọng số và phân tích độ nhạy.

    score(option) = sum(weight[c] * scores[option][c] for c in criteria),  sum(weights) == 1

Chạy thử với matrix.yaml của bạn:
    uv run python tracks/data-engineer/modules/00-introduction/exercises/advanced/01-technology-decision-matrix/starter/decision_matrix.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

Scores = dict[str, dict[str, float]]   # option -> criterion -> điểm 1..5
Weights = dict[str, float]             # criterion -> trọng số, tổng bằng 1


def validate(scores: Scores, weights: Weights) -> None:
    """ValueError nếu: tổng trọng số khác 1 (sai số 1e-6), trọng số âm, phương án thiếu/thừa tiêu chí,
    hoặc điểm ngoài khoảng 1..5."""
    # TODO
    raise NotImplementedError


def weighted_scores(scores: Scores, weights: Weights) -> dict[str, float]:
    """Điểm có trọng số của từng phương án (gọi validate trước)."""
    # TODO
    raise NotImplementedError


def rank(scores: Scores, weights: Weights) -> list[tuple[str, float]]:
    """[(phương án, điểm)] giảm dần theo điểm; bằng điểm thì theo tên phương án."""
    # TODO
    raise NotImplementedError


def reweight(weights: Weights, criterion: str, value: float) -> Weights:
    """Đặt trọng số của `criterion` thành `value` (0..1), các tiêu chí còn lại co giãn THEO TỈ LỆ CŨ để tổng vẫn bằng 1."""
    # TODO
    raise NotImplementedError


def flip_point(scores: Scores, weights: Weights, criterion: str) -> float | None:
    """Trọng số của `criterion` (dùng reweight) gần với trọng số hiện tại nhất mà tại đó phương án đứng đầu
    bắt đầu đổi, chính xác tới 1e-3; None nếu trên cả khoảng [0, 1] phương án đứng đầu không đổi."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    data = yaml.safe_load((Path(__file__).parent / "matrix.yaml").read_text(encoding="utf-8"))
    print(rank(data["scores"], data["weights"]))
    for c in data["weights"]:
        print(c, flip_point(data["scores"], data["weights"], c))
