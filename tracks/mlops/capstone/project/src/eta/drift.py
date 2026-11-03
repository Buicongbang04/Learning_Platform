import pandas as pd


def psi(ref: pd.Series, cur: pd.Series, bins: int = 10) -> float:
    raise NotImplementedError("M10: PSI với biên bin theo quantile của ref, bin rỗng nâng lên 1e-4")


def drift_table(ref: pd.DataFrame, cur: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    raise NotImplementedError("M10: mỗi cột một dòng: feature, psi, ks_stat")
