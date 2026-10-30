import os
import re
import tempfile
import uuid
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest
import statsmodels.formula.api as smf

from testkit import Exercise

ex = Exercise(__file__)
MEMO_HEADINGS = ["## Trả lời ngắn", "## Con số của agency", "## Ước lượng DiD", "## Kiểm tra độ tin cậy",
                 "## Khuyến nghị", "## Giới hạn"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("did_claim.ipynb")


def lines_fixture():
    t = pd.Timestamp
    rows = [
        (1, "2011-01-03 10:00", "Germany"), (1, "2011-01-05 10:00", "Germany"),   # cùng khách, cùng tuần: đếm 1
        (2, "2011-01-09 23:00", "Germany"),                                        # Chủ nhật: vẫn tuần 3-9/1
        (3, "2011-01-04 10:00", "Austria"),                                        # Áo thuộc nhóm "dach"
        (10, "2011-01-04 10:00", "France"), (11, "2011-01-11 10:00", "France"),
        (12, "2011-01-12 10:00", "Spain"),
        (20, "2011-01-12 10:00", "United Kingdom"),                                # không thuộc nhóm nào
        (2, "2011-01-31 10:00", "Germany"),                                        # tuần 31/1: Đức có, đối chứng 0
        (13, "2011-02-07 00:00", "France"),                                        # đúng lúc end: loại
        (14, "2011-01-02 23:59", "France"),                                        # trước start: loại
    ]
    return pd.DataFrame({"customer_id": [float(r[0]) for r in rows],
                         "invoice_date": [t(r[1]) for r in rows],
                         "country": [r[2] for r in rows]})


GROUPS_FX = {"dach": ["Germany", "Austria"], "rest": ["France", "Spain"]}


def test_weekly_active(nb):
    lines = lines_fixture()
    before = lines.copy()
    out = nb.weekly_active(lines, GROUPS_FX, "2011-01-03", "2011-02-07")
    assert list(out.columns) == ["dach", "rest"]
    assert out.index.name == "week"
    assert [str(w) for w in out.index] == ["2011-01-03/2011-01-09", "2011-01-10/2011-01-16", "2011-01-31/2011-02-06"]
    assert out["dach"].tolist() == [3, 0, 1]
    assert out["rest"].tolist() == [1, 2, 0]
    assert pd.api.types.is_integer_dtype(out["dach"]) and pd.api.types.is_integer_dtype(out["rest"])
    pd.testing.assert_frame_equal(lines, before)
    swapped = nb.weekly_active(lines, {"rest": ["France", "Spain"], "dach": ["Germany", "Austria"]},
                               "2011-01-03", "2011-02-07")
    assert list(swapped.columns) == ["rest", "dach"]


def weekly_fixture():
    weeks = pd.period_range("2011-01-03", periods=8, freq="W-SUN")
    return pd.DataFrame({"t": [4, 6, 5, 5, 12, 10, 11, 11], "c": [10, 10, 10, 10, 15, 15, 15, 15]},
                        index=pd.PeriodIndex(weeks, name="week"))


def test_did_table(nb):
    w = weekly_fixture()
    before = w.copy()
    out = nb.did_table(w, "t", "c", "2011-01-31")  # 4 tuần trước, 4 tuần sau
    assert out["pre_treated"] == pytest.approx(5.0)
    assert out["post_treated"] == pytest.approx(11.0)
    assert out["change_treated"] == pytest.approx(1.2)
    assert out["change_control"] == pytest.approx(0.5)
    assert out["did_log"] == pytest.approx(np.log(11 / 5) - np.log(1.5))
    assert out["did"] == pytest.approx((11 / 5) / 1.5 - 1)
    pd.testing.assert_frame_equal(w, before)
    # mốc giữa tuần: tuần chứa mốc (bắt đầu trước mốc) vẫn là "trước"
    mid = nb.did_table(w, "t", "c", "2011-01-26")
    assert mid["pre_treated"] == pytest.approx(5.0)


def test_did_regression_matches_statsmodels(nb):
    rng = np.random.default_rng(5)
    weeks = pd.period_range("2011-01-03", periods=30, freq="W-SUN")
    c = rng.integers(10, 30, 30)
    t = np.maximum(1, np.round(c * 0.4 * np.where(np.arange(30) >= 20, 1.3, 1.0) * rng.lognormal(0, 0.2, 30)))
    w = pd.DataFrame({"de": t.astype(int), "eu": c}, index=pd.PeriodIndex(weeks, name="week"))
    cutoff = weeks[20].start_time
    out = nb.did_regression(w, "de", "eu", cutoff)
    data = pd.DataFrame({"gap": np.log(w["de"]) - np.log(w["eu"]), "post": (np.arange(30) >= 20).astype(int)})
    ref = smf.ols("gap ~ post", data).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    assert out["effect_log"] == pytest.approx(ref.params["post"])
    assert out["ci_low"] == pytest.approx(ref.conf_int().loc["post", 0])
    assert out["ci_high"] == pytest.approx(ref.conf_int().loc["post", 1])
    assert out["p"] == pytest.approx(ref.pvalues["post"])
    assert out["effect"] == pytest.approx(np.exp(ref.params["post"]) - 1)
    lag2 = nb.did_regression(w, "de", "eu", cutoff, maxlags=2)
    ref2 = smf.ols("gap ~ post", data).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    assert lag2["ci_low"] == pytest.approx(ref2.conf_int().loc["post", 0])
    # DiD trên log của 2x2 (log của trung bình) khác hồi quy (trung bình của log) nhưng cùng chiều ở đây
    assert nb.did_table(w, "de", "eu", cutoff)["did"] > 0


# Bản chuẩn của loader Online Retail II cho module 11 (cùng tệp cache với module 03).
# Bài advanced/01-experiment-brief và advanced/02-did-campaign-claim chép y hệt; sửa thì sửa cả ba.
SHEETS = ("Year 2009-2010", "Year 2010-2011")  # sheet đầu chứa lại 01-09/12/2010 của sheet sau: bỏ phần trùng
CACHE_DIR = Path(tempfile.gettempdir()) / "da-cache"  # cache parquet dùng chung với module 03, không ghi vào data/raw


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


def load_online_retail(xlsx: Path) -> pd.DataFrame:
    """Hai sheet Online Retail II gộp (chưa lọc), cột snake_case: invoice, stock_code, description, quantity,
    invoice_date, price, customer_id, country.

    Lần đầu đọc xlsx bằng extension excel của DuckDB (~8 giây; máy không cài được extension thì pandas ~60-90 giây)
    rồi ghi cache parquet vào thư mục tạm của hệ điều hành, khoá theo mtime và kích thước tệp; lần sau ~1 giây.
    """
    stat = xlsx.stat()
    cache = CACHE_DIR / f"online_retail_ii_{stat.st_mtime_ns}_{stat.st_size}.parquet"
    con = duckdb.connect()
    if cache.exists():
        try:
            return con.execute(f"SELECT * FROM read_parquet('{_sql_path(cache)}')").df()
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
        old, new = (pd.read_excel(xlsx, sheet_name=s) for s in SHEETS)
        raw = pd.concat([old[old.InvoiceDate < "2010-12-01"], new], ignore_index=True)
        frame = pd.DataFrame({
            "invoice": raw["Invoice"].astype(str), "stock_code": raw["StockCode"].astype(str),
            "description": raw["Description"], "quantity": raw["Quantity"].astype("int32"),
            "invoice_date": raw["InvoiceDate"], "price": raw["Price"].astype(float),
            "customer_id": raw["Customer ID"].astype("Int32"), "country": raw["Country"],
        })
        con.register("frame", frame)
        con.execute("CREATE TABLE online_retail AS SELECT * FROM frame")
    tmp = CACHE_DIR / f".{cache.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:  # ghi atomic: tệp tạm tên riêng rồi rename, an toàn khi nhiều tiến trình cùng ghi
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        con.execute(f"COPY online_retail TO '{_sql_path(tmp)}' (FORMAT parquet)")
        os.replace(tmp, cache)
    except (OSError, duckdb.Error):  # không ghi được cache thì thôi, lần sau đọc lại xlsx
        tmp.unlink(missing_ok=True)
    return con.execute("SELECT * FROM online_retail").df()


@pytest.fixture(scope="module")
def real_lines(nb):
    raw = load_online_retail(ex.dataset("online-retail-ii") / "online_retail_II.xlsx")
    return nb.valid_customer_lines(raw)  # hàm viết sẵn: fixture không gọi hàm TODO để starter chỉ FAIL, không ERROR


def test_real_did(nb, real_lines):
    weekly = nb.weekly_active(real_lines, nb.GROUPS, "2011-02-28", "2011-11-28")
    assert len(weekly) == 39
    assert weekly.sum().tolist() == [304, 763]
    table = nb.did_table(weekly, "germany", "control", "2011-09-01")
    assert table["change_treated"] == pytest.approx(0.6810, abs=1e-4)  # con số "68%" của agency
    assert table["change_control"] == pytest.approx(0.5650, abs=1e-4)
    assert table["did"] == pytest.approx(0.0741, abs=1e-4)
    reg = nb.did_regression(weekly, "germany", "control", "2011-09-01")
    assert reg["effect_log"] == pytest.approx(0.1000, abs=1e-4)
    assert reg["ci_low"] == pytest.approx(-0.0653, abs=1e-4)
    assert reg["p"] == pytest.approx(0.2357, abs=1e-3)


def test_real_placebo(nb, real_lines):
    last_year = nb.weekly_active(real_lines, nb.GROUPS, "2010-03-01", "2010-11-29")
    table = nb.did_table(last_year, "germany", "control", "2010-09-01")
    assert table["change_treated"] == pytest.approx(0.4559, abs=1e-4)
    assert table["did"] == pytest.approx(-0.1364, abs=1e-4)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 600, f"Memo một trang: 200-600 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
