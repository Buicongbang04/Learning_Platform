from typing import Callable

import numpy as np
import pandas as pd

Predict = Callable[[pd.DataFrame], np.ndarray]


def column_order_shift(predict: Predict, X: pd.DataFrame) -> float:
    # TODO: so dự đoán trên X với dự đoán trên X có thứ tự cột đảo ngược; trả chênh lệch tuyệt đối lớn nhất.
    # Không được sửa X tại chỗ.
    raise NotImplementedError


def distance_effect(predict: Predict, X: pd.DataFrame, factor: float = 1.2, column: str = "trip_distance") -> tuple[float, float]:
    # TODO: nhân cột `column` với `factor`, giữ nguyên mọi cột khác. Trả (mean_delta, violation_rate):
    # mean_delta là trung bình của (dự đoán mới - dự đoán cũ), violation_rate là tỉ lệ chuyến có dự đoán mới thấp hơn cũ.
    # Không được sửa X tại chỗ.
    raise NotImplementedError


def assert_column_order_invariant(predict: Predict, X: pd.DataFrame, tol: float = 1e-9) -> None:
    # TODO: AssertionError (thông báo có số đo được) nếu column_order_shift lớn hơn tol
    raise NotImplementedError


def assert_distance_monotonic(predict: Predict, X: pd.DataFrame, factor: float = 1.2, max_violation_rate: float = 0.2) -> None:
    # TODO: AssertionError (thông báo có số đo được) nếu mean_delta < 0 hoặc violation_rate > max_violation_rate
    raise NotImplementedError
