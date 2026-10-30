"""Chạy thử một tệp .sql của bài trên dữ liệu thật rồi in kết quả. Tệp này không được chấm.

Nạp bộ `online-retail-ii` vào DuckDB trong bộ nhớ (bảng: online_retail), chạy tệp .sql và in các dòng đầu:

    uv run python <thư mục bài>/starter/run_query.py cohort_retention.sql
    uv run python <thư mục bài>/starter/run_query.py cohort_retention.sql --rows 100
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import uuid
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT))
from data.download_dataset import ensure  # noqa: E402

# Bản chuẩn của loader Online Retail II: exercises/basic/01-monthly-revenue-mom/tests/test_monthly.py.
# Các bài khác của module chép y hệt; sửa thì sửa mọi bản.
SHEETS = ("Year 2009-2010", "Year 2010-2011")  # sheet đầu chứa lại 01-09/12/2010 của sheet sau: bỏ phần trùng
CACHE_DIR = Path(tempfile.gettempdir()) / "da-cache"  # cache parquet, không ghi vào data/raw (thư mục dùng chung)


def _sql_path(path: Path) -> str:
    return str(path).replace("'", "''")


def _sheet_sql(xlsx: Path, sheet: str) -> str:
    return f"""
        SELECT Invoice AS invoice, StockCode AS stock_code, Description AS description,
               CAST(CAST(Quantity AS DOUBLE) AS INTEGER) AS quantity,
               TIMESTAMP '1899-12-30' + to_seconds(CAST(round(CAST(InvoiceDate AS DOUBLE) * 86400) AS BIGINT))
                   AS invoice_date,
               CAST(Price AS DOUBLE) AS price,
               CAST(CAST("Customer ID" AS DOUBLE) AS INTEGER) AS customer_id,
               Country AS country
        FROM read_xlsx('{_sql_path(xlsx)}', sheet = '{sheet}', all_varchar = true)"""


def _excel_extension_missing(exc: duckdb.Error) -> bool:
    """Chỉ lỗi cài/nạp extension excel (máy offline...). Lỗi SQL hay lỗi dữ liệu thì phải nổi lên."""
    kinds = (duckdb.CatalogException, duckdb.IOException, duckdb.HTTPException)
    return isinstance(exc, kinds) and "extension" in str(exc).lower()


def _load_with_pandas(con: duckdb.DuckDBPyConnection, xlsx: Path) -> None:
    import pandas as pd

    old, new = (pd.read_excel(xlsx, sheet_name=s) for s in SHEETS)
    df = pd.concat([old[old.InvoiceDate < "2010-12-01"], new], ignore_index=True)
    df = pd.DataFrame({
        "invoice": df["Invoice"].astype(str), "stock_code": df["StockCode"].astype(str),
        "description": df["Description"], "quantity": df["Quantity"].astype("int32"),
        "invoice_date": df["InvoiceDate"], "price": df["Price"].astype(float),
        "customer_id": df["Customer ID"].astype("Int32"), "country": df["Country"],
    })
    con.register("online_retail_df", df)
    con.execute("CREATE TABLE online_retail AS SELECT * FROM online_retail_df")
    con.unregister("online_retail_df")


def load_online_retail(con: duckdb.DuckDBPyConnection, xlsx: Path) -> None:
    """Bảng `online_retail`: hai sheet gộp, đúng dữ liệu gốc (chưa lọc hoá đơn huỷ, giá 0...).

    Lần đầu đọc xlsx (extension excel của DuckDB ~8 giây; máy không cài được extension thì pandas ~60-90 giây)
    rồi ghi cache parquet vào thư mục tạm của hệ điều hành, khoá theo mtime và kích thước tệp xlsx; các lần sau
    đọc cache trong khoảng 1 giây.
    """
    stat = xlsx.stat()
    cache = CACHE_DIR / f"online_retail_ii_{stat.st_mtime_ns}_{stat.st_size}.parquet"
    if cache.exists():
        try:
            con.execute(f"CREATE TABLE online_retail AS SELECT * FROM read_parquet('{_sql_path(cache)}')")
            return
        except duckdb.IOException:  # cache hỏng: đọc lại từ xlsx và ghi đè
            pass
    try:
        con.execute(
            f"CREATE TABLE online_retail AS SELECT * FROM ({_sheet_sql(xlsx, SHEETS[0])}) "
            f"WHERE invoice_date < TIMESTAMP '2010-12-01' UNION ALL {_sheet_sql(xlsx, SHEETS[1])}"
        )
    except duckdb.Error as exc:
        if not _excel_extension_missing(exc):
            raise
        _load_with_pandas(con, xlsx)
    tmp = CACHE_DIR / f".{cache.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:  # ghi atomic: tệp tạm tên riêng rồi rename, an toàn khi nhiều test chạy song song
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        con.execute(f"COPY online_retail TO '{_sql_path(tmp)}' (FORMAT parquet)")
        os.replace(tmp, cache)
    except (OSError, duckdb.Error):  # không ghi được cache thì thôi, lần sau đọc lại xlsx
        tmp.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sql", help="tệp .sql (tên tệp trong starter/ hoặc đường dẫn)")
    parser.add_argument("--rows", type=int, default=40, help="số dòng in ra")
    args = parser.parse_args()
    path = Path(args.sql)
    if not path.exists():
        path = HERE / args.sql
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    load_online_retail(con, ensure("online-retail-ii") / "online_retail_II.xlsx")
    result = con.sql(path.read_text(encoding="utf-8")).df()
    print(result.head(args.rows).to_string())
    print(f"({len(result)} dòng)")


if __name__ == "__main__":
    main()
