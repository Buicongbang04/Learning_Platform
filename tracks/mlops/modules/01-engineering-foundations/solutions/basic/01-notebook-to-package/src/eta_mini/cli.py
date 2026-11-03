import argparse
import json

import joblib

from eta_mini.data import clean, load_trips
from eta_mini.model import train


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eta-train")
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-rows", type=int, default=None)
    args = parser.parse_args(argv)
    trips = clean(load_trips(args.data, max_rows=args.max_rows, seed=args.seed))
    result = train(trips, seed=args.seed)
    joblib.dump(result.model, args.out)
    print(json.dumps({"mae": result.mae, "n_train": result.n_train, "n_test": result.n_test}))
    return 0
