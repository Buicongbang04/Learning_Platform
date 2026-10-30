"""Nạp dữ liệu mẫu cho BI vào Postgres schema `da` (chạy lại được: thay bảng cũ).

    uv run python setup/bi/load_da.py

Bảng:
- da.online_retail_ii : dòng hợp lệ của Online Retail II (bỏ Invoice bắt đầu bằng "C", Quantity <= 0, Price <= 0),
                        thêm cột revenue = quantity * price
- da.bike_hour        : Bike Sharing UCI (hour.csv)
Cần Postgres đang chạy (xem setup/SETUP.md) và dữ liệu đã tải (data/download_dataset.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import testkit  # noqa: E402

RETAIL = ROOT / "data/raw/online-retail-ii/online_retail_II.xlsx"
BIKE = ROOT / "data/raw/bike-sharing-uci/hour.csv"


def clean_retail(frames: list[pd.DataFrame]) -> pd.DataFrame:
    # Hai sheet trùng nhau ở 2010-12-01..09: giữ phần trùng từ sheet đầu, bỏ khỏi sheet sau.
    first, rest = frames[0], frames[1:]
    cutoff = first["InvoiceDate"].max()
    df = pd.concat([first] + [f[f["InvoiceDate"] > cutoff] for f in rest], ignore_index=True)
    df["Invoice"] = df["Invoice"].astype(str)
    df = df[~df["Invoice"].str.startswith("C") & (df["Quantity"] > 0) & (df["Price"] > 0)]
    df = df.rename(columns={"Customer ID": "customer_id"})
    df.columns = [c.lower() for c in df.columns]
    df["customer_id"] = df["customer_id"].astype("Int64")
    df["stockcode"] = df["stockcode"].astype(str)
    df["revenue"] = df["quantity"] * df["price"]
    return df.reset_index(drop=True)


def main() -> None:
    engine = create_engine(testkit.POSTGRES_DSN.replace("postgresql://", "postgresql+psycopg://", 1))
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS da"))

    sheets = pd.read_excel(RETAIL, sheet_name=None)  # đọc xlsx một lần, cả hai sheet
    retail = clean_retail(list(sheets.values()))
    bike = pd.read_csv(BIKE)

    with engine.begin() as conn:
        retail.to_sql("online_retail_ii", conn, schema="da", if_exists="replace", index=False, chunksize=50_000)
        bike.to_sql("bike_hour", conn, schema="da", if_exists="replace", index=False)
        conn.execute(text("GRANT USAGE ON SCHEMA da TO PUBLIC"))
        conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA da TO PUBLIC"))
    with engine.connect() as conn:
        for t in ("online_retail_ii", "bike_hour"):
            n = conn.execute(text(f"SELECT count(*) FROM da.{t}")).scalar()
            print(f"da.{t}: {n} dòng")


if __name__ == "__main__":
    main()
