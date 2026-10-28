"""Quality gate cho bảng orders bằng pandera (lời giải)."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

ORDER_STATUSES = ["created", "approved", "invoiced", "processing", "shipped",
                  "delivered", "canceled", "unavailable"]
FAILURE_COLUMNS = ["index", "column", "check", "failure_case"]


def _delivered_after_purchase(df: pd.DataFrame) -> pd.Series:
    delivered = df["order_delivered_customer_date"]
    return delivered.isna() | (delivered >= df["order_purchase_timestamp"])


def build_orders_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        {
            "order_id": pa.Column(str, nullable=False, unique=True),
            "customer_id": pa.Column(str, nullable=False),
            "order_status": pa.Column(str, pa.Check.isin(ORDER_STATUSES)),
            "order_purchase_timestamp": pa.Column("datetime64[ns]", nullable=False, coerce=True),
            "order_delivered_customer_date": pa.Column("datetime64[ns]", nullable=True, coerce=True),
            "price": pa.Column(float, pa.Check.gt(0)),
            "freight_value": pa.Column(float, pa.Check.ge(0)),
        },
        checks=[pa.Check(_delivered_after_purchase, name="delivered_after_purchase")],
        strict=False,
    )


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Trả (valid_df, failures)."""
    try:
        build_orders_schema().validate(df, lazy=True)
    except pa.errors.SchemaErrors as err:
        failures = err.failure_cases[FAILURE_COLUMNS].reset_index(drop=True)
    else:
        failures = pd.DataFrame(columns=FAILURE_COLUMNS)
    bad_index = set(failures["index"].dropna().astype(int))
    valid = df[~df.index.isin(bad_index)]
    return valid, failures


def quality_report(df: pd.DataFrame) -> dict:
    valid, failures = validate(df)
    rows_with_index = failures.dropna(subset=["index"])
    failed_checks = (
        rows_with_index.groupby("check")["index"].nunique().astype(int).to_dict()
        if len(rows_with_index) else {}
    )
    return {
        "rows": len(df),
        "valid_rows": len(valid),
        "invalid_rows": len(df) - len(valid),
        "failed_checks": {str(k): int(v) for k, v in failed_checks.items()},
    }
