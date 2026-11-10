import sys
from pathlib import Path

import joblib

from app.etaml import FEATURES, RELEASES, make_trips, release_model


def build(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for version, (seed, _, rows) in RELEASES.items():
        reference, _ = make_trips(seed, rows)
        bundle = {"version": version, "features": FEATURES, "model": release_model(version), "reference": reference}
        joblib.dump(bundle, folder / f"eta-{version}.joblib")


if __name__ == "__main__":
    build(Path(sys.argv[1]))
