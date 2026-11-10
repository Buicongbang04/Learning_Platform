import numpy as np
import pandas as pd


def labeled_mae(df, now, delay_days):
    ready = df[df["ts"] + pd.Timedelta(days=delay_days) <= now]
    if ready.empty:
        return None
    return float((ready["pred"] - ready["label"]).abs().mean())


def seasonal_baseline(daily, day, weeks=4):
    values = [daily[day - pd.Timedelta(days=7 * k)] for k in range(1, weeks + 1) if day - pd.Timedelta(days=7 * k) in daily.index]
    if len(values) < 2:
        raise ValueError("cần ít nhất 2 ngày cùng thứ trong quá khứ")
    return float(np.mean(values)), float(np.std(values, ddof=1))


def proxy_alerts(pred_mean, fallback_rate, day, z_limit=3.0, fallback_limit=0.02, weeks=4):
    reasons = []
    mean, std = seasonal_baseline(pred_mean, day, weeks)
    if abs(pred_mean[day] - mean) / std > z_limit:
        reasons.append("pred_mean")
    base_fallback, _ = seasonal_baseline(fallback_rate, day, weeks)
    if fallback_rate[day] > base_fallback + fallback_limit:
        reasons.append("fallback")
    return reasons
