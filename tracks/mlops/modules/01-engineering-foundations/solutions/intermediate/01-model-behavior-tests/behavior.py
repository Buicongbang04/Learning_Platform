from typing import Callable

import numpy as np
import pandas as pd

Predict = Callable[[pd.DataFrame], np.ndarray]


def column_order_shift(predict: Predict, X: pd.DataFrame) -> float:
    reordered = X[list(X.columns[::-1])]
    return float(np.max(np.abs(np.asarray(predict(X)) - np.asarray(predict(reordered)))))


def distance_effect(predict: Predict, X: pd.DataFrame, factor: float = 1.2, column: str = "trip_distance") -> tuple[float, float]:
    longer = X.copy()
    longer[column] = longer[column] * factor
    delta = np.asarray(predict(longer)) - np.asarray(predict(X))
    return float(delta.mean()), float((delta < 0).mean())


def assert_column_order_invariant(predict: Predict, X: pd.DataFrame, tol: float = 1e-9) -> None:
    shift = column_order_shift(predict, X)
    assert shift <= tol, f"Đổi thứ tự cột làm dự đoán lệch tối đa {shift:.6f} (cho phép {tol})"


def assert_distance_monotonic(predict: Predict, X: pd.DataFrame, factor: float = 1.2, max_violation_rate: float = 0.2) -> None:
    mean_delta, violation_rate = distance_effect(predict, X, factor)
    assert mean_delta >= 0, f"Tăng khoảng cách x{factor} làm ETA trung bình giảm {mean_delta:.3f} phút"
    assert violation_rate <= max_violation_rate, f"{violation_rate:.1%} chuyến có ETA giảm khi tăng khoảng cách (cho phép {max_violation_rate:.0%})"
