import pandas as pd

SCHEMA = None


def validate_month(df: pd.DataFrame, month: str) -> None:
    raise NotImplementedError("M03: schema Pandera + kiểm theo tháng, raise pandera.errors.SchemaErrors")
