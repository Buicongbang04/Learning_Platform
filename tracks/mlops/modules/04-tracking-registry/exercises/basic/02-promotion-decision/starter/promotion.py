from dataclasses import dataclass, field

DEFAULT_POLICY = {
    "min_improvement": 0.01,
    "slice_tolerance": 0.05,
    "min_slice_n": 200,
    "max_latency_ratio": 1.2,
    "max_latency_ms": None,
    "max_mae": None,
}


@dataclass
class Decision:
    promote: bool
    reasons: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)


def decide_promotion(challenger: dict, champion: dict | None, policy: dict | None = None) -> Decision:
    """Quyết định có cho challenger thay champion không.

    challenger / champion: {"mae": float, "latency_p95_ms": float,
                            "slices": {"<tên>": {"mae": float, "n": int}}}
    policy: ghi đè từng khoá của DEFAULT_POLICY.

    Trả Decision với `checks` có đúng ba khoá "overall_mae", "slices", "latency" và `reasons`
    có một dòng cho mỗi check trượt (nêu tên slice trượt), hoặc một dòng tóm tắt khi promote.
    """
    # TODO
    raise NotImplementedError
