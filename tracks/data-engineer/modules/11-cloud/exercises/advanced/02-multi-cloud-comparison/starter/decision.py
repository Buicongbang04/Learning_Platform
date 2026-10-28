"""Ma trận quyết định có trọng số để chọn cloud."""

from __future__ import annotations

CLOUDS = ("aws", "azure", "gcp")

# TODO 1: điểm 1-5 cho mỗi cloud, cùng một bộ >= 5 tiêu chí, bắt buộc có "cost" và "team_skills"
SCORES: dict[str, dict[str, int]] = {
    "aws": {},
    "azure": {},
    "gcp": {},
}

# TODO 2: trọng số không âm cho đúng các tiêu chí trên
WEIGHTS: dict[str, float] = {}


def weighted_scores(scores: dict[str, dict[str, float]], weights: dict[str, float]) -> dict[str, float]:
    # TODO 3: kiểm tra lỗi -> ValueError; chuẩn hoá trọng số; trung bình có trọng số, làm tròn 3 chữ số
    raise NotImplementedError


def rank(scores: dict[str, dict[str, float]], weights: dict[str, float]) -> list[tuple[str, float]]:
    # TODO 4: giảm dần theo điểm, hoà thì theo tên cloud tăng dần
    raise NotImplementedError


if __name__ == "__main__":
    for cloud, score in rank(SCORES, WEIGHTS):
        print(f"{cloud:>6}: {score:.3f}")
