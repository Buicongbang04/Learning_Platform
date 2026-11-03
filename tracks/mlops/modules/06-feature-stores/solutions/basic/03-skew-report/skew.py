import numpy as np
import pandas as pd


def skew_report(offline: pd.DataFrame, online: pd.DataFrame, key: str, rtol: float = 1e-6, atol: float = 1e-9) -> list[dict]:
    report = []
    off_cols = set(offline.columns) - {key}
    on_cols = set(online.columns) - {key}
    for column in sorted(off_cols ^ on_cols):
        report.append({"column": column, "kind": "missing_column", "mismatch_rate": 1.0, "max_abs_diff": None})
    keys_off, keys_on = set(offline[key]), set(online[key])
    union = keys_off | keys_on
    if union and keys_off != keys_on:
        report.append(
            {"column": "__rows__", "kind": "row_coverage", "mismatch_rate": len(keys_off ^ keys_on) / len(union), "max_abs_diff": None}
        )
    joined = offline.merge(online, on=key, how="inner", suffixes=("_off", "_on"))
    for column in sorted(off_cols & on_cols):
        a, b = joined[f"{column}_off"], joined[f"{column}_on"]
        null_gap = a.isna() ^ b.isna()
        both = ~(a.isna() | b.isna())
        numeric = pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b)
        if numeric:
            av, bv = a.to_numpy(dtype="float64", na_value=np.nan), b.to_numpy(dtype="float64", na_value=np.nan)
            differs = both.to_numpy() & ~np.isclose(av, bv, rtol=rtol, atol=atol, equal_nan=True)
            diff = np.abs(av - bv)[differs]
            max_diff = float(diff.max()) if diff.size else None
        else:
            differs = both.to_numpy() & (a.to_numpy() != b.to_numpy())
            max_diff = None
        bad = null_gap.to_numpy() | differs
        if not bad.any():
            continue
        kind = "null_mismatch" if null_gap.any() else "value_mismatch"
        report.append({"column": column, "kind": kind, "mismatch_rate": float(bad.mean()), "max_abs_diff": max_diff})
    return sorted(report, key=lambda item: (-item["mismatch_rate"], item["column"]))
