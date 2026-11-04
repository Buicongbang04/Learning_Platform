import numpy as np

__version__ = "1.4.0"


def standardize(x):
    x = np.asarray(x, dtype=float)
    return (x - x.mean(axis=0)) / x.std(axis=0)
