import json
import sys

import numpy as np
import scalekit


def main() -> None:
    seed, alpha, out = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    rng = np.random.default_rng(seed)
    weights = np.array([1.5, -2.0, 0.7])
    x = rng.standard_t(3, size=(300, 3))
    y = x @ weights + rng.normal(0, 0.5, size=300)
    holdout = np.random.default_rng(12345).standard_t(3, size=(50, 3))
    z = scalekit.standardize(x)
    gram = z.T @ z + alpha * np.eye(3)
    coef = np.linalg.solve(gram, z.T @ (y - y.mean()))
    zh = (holdout - x.mean(axis=0)) / x.std(axis=0)
    preds = zh @ coef + y.mean()
    with open(out, "w", encoding="utf-8") as fh:
        json.dump([float(p) for p in preds], fh)


if __name__ == "__main__":
    main()
