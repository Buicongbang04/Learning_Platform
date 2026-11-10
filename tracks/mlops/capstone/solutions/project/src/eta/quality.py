import numpy as np
import pandas as pd

from eta.features import AIRPORT_ZONES


def join_labels(predictions: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    truth = labels[["request_id", "duration_s"]].drop_duplicates("request_id")
    return predictions.merge(truth, on="request_id", how="inner", validate="many_to_one")


def monthly_quality(joined: pd.DataFrame) -> dict[str, float]:
    err = (joined["eta_s"].astype("float64") - joined["duration_s"].astype("float64")).to_numpy()
    if len(err) == 0:
        return {"mae": float("nan"), "p90_abs_err": float("nan"), "mae_airport": float("nan"), "bias_s": float("nan"), "n": 0}
    abs_err = np.abs(err)
    airport = (joined["PULocationID"].isin(AIRPORT_ZONES) | joined["DOLocationID"].isin(AIRPORT_ZONES)).to_numpy()
    return {
        "mae": float(abs_err.mean()),
        "p90_abs_err": float(np.quantile(abs_err, 0.9)),
        "mae_airport": float(abs_err[airport].mean()) if airport.any() else float("nan"),
        "bias_s": float(err.mean()),
        "n": int(len(err)),
    }


SUMMARY_COLUMNS = ["month", "model_version", "n_scored", "psi_trip_distance", "psi_pickup_hour", "psi_eta_s",
                   "ks_trip_distance", "n_labeled", "mae", "p90_abs_err", "mae_airport", "bias_s", "as_of"]


def _drift_frame(predictions: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "trip_distance": predictions["trip_distance"].astype("float64"),
        "pickup_hour": pd.to_datetime(predictions["pickup_datetime"]).dt.hour.astype("float64"),
        "eta_s": predictions["eta_s"].astype("float64"),
    })


def replay_summary(months: list[str], reference_month: str, as_of: str, config, out_dir) -> pd.DataFrame:
    from pathlib import Path

    from eta.drift import drift_table
    from eta.labels import labels_for

    out = Path(out_dir)
    reference = _drift_frame(pd.read_parquet(out / f"predictions_{reference_month}.parquet"))
    rows = []
    for month in months:
        scored = pd.read_parquet(out / f"predictions_{month}.parquet")
        drift = drift_table(reference, _drift_frame(scored), ["trip_distance", "pickup_hour", "eta_s"]).set_index("feature")
        truth = labels_for(month, as_of, config)
        quality = monthly_quality(join_labels(scored, truth)) if truth is not None else None
        rows.append({
            "month": month,
            "model_version": str(scored["model_version"].iloc[0]),
            "n_scored": int(len(scored)),
            "psi_trip_distance": float(drift.loc["trip_distance", "psi"]),
            "psi_pickup_hour": float(drift.loc["pickup_hour", "psi"]),
            "psi_eta_s": float(drift.loc["eta_s", "psi"]),
            "ks_trip_distance": float(drift.loc["trip_distance", "ks_stat"]),
            "n_labeled": quality["n"] if quality else 0,
            "mae": quality["mae"] if quality else float("nan"),
            "p90_abs_err": quality["p90_abs_err"] if quality else float("nan"),
            "mae_airport": quality["mae_airport"] if quality else float("nan"),
            "bias_s": quality["bias_s"] if quality else float("nan"),
            "as_of": as_of,
        })
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
