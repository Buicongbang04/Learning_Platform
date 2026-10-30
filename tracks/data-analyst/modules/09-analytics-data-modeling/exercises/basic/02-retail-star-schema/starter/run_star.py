"""Dựng star schema từ star_schema.sql trên dữ liệu thật rồi in vài con số để tự kiểm. Tệp này không được chấm.

    uv run python tracks/data-analyst/modules/09-analytics-data-modeling/exercises/basic/02-retail-star-schema/starter/run_star.py

Lần đầu đọc xlsx mất 30-60 giây; sau đó đọc cache parquet trong thư mục tạm.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT))
from data.download_dataset import ensure  # noqa: E402


def load_retail_2010_2011() -> pd.DataFrame:
    xlsx = ensure("online-retail-ii") / "online_retail_II.xlsx"
    st = xlsx.stat()
    cache = Path(tempfile.gettempdir()) / "da-cache" / f"m09_2010-2011_{st.st_mtime_ns}_{st.st_size}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = pd.read_excel(xlsx, sheet_name="Year 2010-2011")
    df.insert(0, "source_row", range(1, len(df) + 1))
    for col in ["Invoice", "StockCode", "Description", "Country"]:
        df[col] = df[col].map(lambda x: None if pd.isna(x) else str(x))
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(f".{uuid.uuid4().hex}.tmp")
    df.to_parquet(tmp)
    os.replace(tmp, cache)
    return df


con = duckdb.connect()
con.register("src", load_retail_2010_2011())
con.execute("CREATE TABLE raw_sales_lines AS SELECT * FROM src")
con.execute((HERE / "star_schema.sql").read_text(encoding="utf-8"))
for table in ["dim_date", "dim_product", "dim_customer", "fct_sales_line"]:
    print(table, con.execute(f"SELECT count(*) FROM {table}").fetchall()[0][0], "dòng")
print(con.sql("""
    SELECT d.current_country = 'Unknown' AS is_guest, p.is_merchandise,
           count(*) AS lines, round(sum(f.revenue), 2) AS revenue
    FROM fct_sales_line f JOIN dim_customer d USING (customer_key) JOIN dim_product p USING (product_key)
    GROUP BY ALL ORDER BY ALL
"""))
