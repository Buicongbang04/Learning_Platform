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


def first_shift_day(df, column):
    daily = df.groupby("day")[column].median()
    previous = daily.shift(1)
    ratio = np.maximum(daily, previous) / np.minimum(daily, previous)
    hits = ratio[ratio > 2]
    return None if hits.empty else hits.index[0]


def shift_ratio(df, column, day):
    before = df.loc[df["day"] < day, column].median()
    after = df.loc[df["day"] >= day, column].median()
    return float(round(before / after))


def harmonize(df, column, day, ratio):
    out = df.copy()
    mask = out["day"] >= day
    out.loc[mask, column] = out.loc[mask, column] * ratio
    return out


def range_guard(df, column, low, high, max_outside=0.05):
    outside = ((df[column] < low) | (df[column] > high)).mean()
    return bool(outside <= max_outside)
