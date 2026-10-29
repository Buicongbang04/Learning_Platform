"""Ước lượng giá trị theo kịch bản, độ nhạy (tornado) và điểm hoà vốn cho memo một trang."""

from __future__ import annotations

from typing import Callable, Mapping

import pandas as pd


def weekly_value(flagged_per_week: float, precision: float, effect: float, loss_event: float,
                 cost_action: float) -> float:
    """Giá trị mỗi tuần (R$): flagged_per_week * (precision * effect * loss_event − cost_action)."""
    # TODO
    raise NotImplementedError


def tornado(fn: Callable[..., float], base: Mapping[str, float],
            ranges: Mapping[str, tuple[float, float]]) -> pd.DataFrame:
    """Với mỗi tham số trong ranges, giữ các tham số khác ở base, tính fn tại cận thấp và cận cao.

    Trả DataFrame cột param, value_low (fn tại cận thấp), value_high (fn tại cận cao),
    swing = |value_high − value_low|; sắp swing giảm dần, index 0..n-1.
    """
    # TODO
    raise NotImplementedError


def scenarios(fn: Callable[..., float], base: Mapping[str, float],
              ranges: Mapping[str, tuple[float, float]]) -> dict[str, float]:
    """{"pessimistic", "base", "optimistic"}: base là fn(**base); pessimistic đặt MỌI tham số trong ranges
    ở cận cho giá trị thấp hơn (xét từng tham số riêng, như tornado), optimistic ở cận cho giá trị cao hơn.
    """
    # TODO
    raise NotImplementedError


def break_even(fn: Callable[..., float], base: Mapping[str, float], param: str, lo: float, hi: float) -> float:
    """Giá trị của `param` trong [lo, hi] làm fn = 0 (các tham số khác ở base), giải bằng
    scipy.optimize.brentq. ValueError nếu fn không đổi dấu trên [lo, hi].
    """
    # TODO
    raise NotImplementedError
