import pandas as pd


def point_in_time_join(
    events: pd.DataFrame,
    features: pd.DataFrame,
    key: str,
    event_ts: str = "event_ts",
    feature_ts: str = "feature_ts",
    tolerance: pd.Timedelta | None = None,
) -> pd.DataFrame:
    left = events.reset_index(drop=True).assign(_order=range(len(events))).sort_values(event_ts, kind="stable")
    right = features.assign(feature_timestamp=features[feature_ts]).sort_values(feature_ts, kind="stable")
    merged = pd.merge_asof(
        left,
        right,
        left_on=event_ts,
        right_on=feature_ts,
        by=key,
        direction="backward",
        allow_exact_matches=True,
        tolerance=tolerance,
    )
    merged = merged.sort_values("_order").drop(columns=["_order", feature_ts])
    return merged.reset_index(drop=True)
