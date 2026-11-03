import numpy as np

__version__ = "1.6.0"


def standardize(x):
    x = np.asarray(x, dtype=float)
    z = (x - x.mean(axis=0)) / x.std(axis=0, ddof=1)
    return np.clip(z, -2.5, 2.5)
