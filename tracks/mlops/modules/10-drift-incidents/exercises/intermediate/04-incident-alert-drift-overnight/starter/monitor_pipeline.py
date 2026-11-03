import numpy as np
import pandas as pd

FEATURES = ["trip_distance", "fare_amount", "trip_time"]
PSI_ALERT = 0.25


def psi(reference, current, bins=10, eps=1e-4):
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    ref_share = np.clip(np.histogram(reference, edges)[0] / len(reference), eps, None)
    cur_share = np.clip(np.histogram(current, edges)[0] / len(current), eps, None)
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def drift_scores(reference, current, columns=FEATURES):
    return {c: psi(reference[c], current[c]) for c in columns}


def drifted_columns(reference, current, columns=FEATURES):
    scores = drift_scores(reference, current, columns)
    return [c for c in columns if scores[c] >= PSI_ALERT]


def change_point_day(df, column):
    # TODO: ngày đầu tiên có trung vị khác ngày liền trước quá 2 lần (luật trong README); None nếu không có
    raise NotImplementedError


def median_ratio(df, column, day):
    # TODO: trung vị trước `day` chia trung vị từ `day` trở đi, làm tròn về số nguyên gần nhất (float)
    raise NotImplementedError


def adjust_from(df, column, day, factor):
    # TODO: bản sao df, nhân cột với factor ở các dòng từ `day` trở đi
    raise NotImplementedError


def range_guard(df, column, low, high, max_outside=0.05):
    # TODO: True nếu tỉ lệ dòng ngoài [low, high] không vượt max_outside, ngược lại False
    raise NotImplementedError
