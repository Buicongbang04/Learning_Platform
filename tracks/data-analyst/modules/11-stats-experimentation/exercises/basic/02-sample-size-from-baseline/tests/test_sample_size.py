import math
import os
import tempfile
import uuid
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("sample_size.ipynb")


def invoices_fixture():
    t = pd.Timestamp
    return pd.DataFrame({
        "customer_id": [1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6],
        "invoice": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"],
        "invoice_date": [
            t("2011-01-05 10:00"), t("2011-02-20 09:00"),   # 1: quay lại sau 46 ngày
            t("2011-01-10 10:00"), t("2011-04-01 10:00"),   # 2: quay lại sau 81 ngày (ngoài 60, trong 90)
            t("2011-01-15 10:00"),                          # 3: không quay lại
            t("2011-03-01 10:00"), t("2011-03-01 10:00"),   # 4: hoá đơn thứ hai cùng giờ: không tính là quay lại
            t("2010-12-20 10:00"), t("2011-01-20 10:00"),   # 5: mua đầu trước cohort_start: không đủ điều kiện
            t("2011-05-20 10:00"), t("2011-06-01 10:00"),   # 6: chưa đủ cửa sổ 60 ngày trước data_end
        ],
        "revenue": [10.0] * 11,
    })


def test_repeat_rate_window_and_eligibility(nb):
    inv = invoices_fixture()
    rate, n = nb.repeat_rate(inv, 60, "2011-01-01", "2011-06-30")
    # đủ điều kiện: 1, 2, 3, 4 (5 mua đầu trước cohort; 6 mua đầu 20/5 + 60 ngày > 30/6)
    assert n == 4
    assert rate == pytest.approx(1 / 4)
    assert isinstance(rate, float) and isinstance(n, int)


def test_repeat_rate_longer_window(nb):
    rate, n = nb.repeat_rate(invoices_fixture(), 90, "2011-01-01", "2011-06-30")
    assert n == 4  # 4 mua đầu 1/3 + 90 ngày = 30/5 <= 30/6
    assert rate == pytest.approx(2 / 4)


def test_repeat_rate_boundary_inclusive(nb):
    t = pd.Timestamp
    inv = pd.DataFrame({"customer_id": [1, 1], "invoice": ["a", "b"],
                        "invoice_date": [t("2011-01-01 10:00"), t("2011-03-02 10:00")], "revenue": [1.0, 1.0]})
    # đúng 60 ngày sau: vẫn tính; data_end đúng bằng ngày đầu + 60: vẫn đủ điều kiện
    assert nb.repeat_rate(inv, 60, "2011-01-01", "2011-03-02 10:00") == (1.0, 1)


def test_repeat_rate_does_not_mutate(nb):
    inv = invoices_fixture()
    before = inv.copy()
    nb.repeat_rate(inv, 60, "2011-01-01", "2011-06-30")
    pd.testing.assert_frame_equal(inv, before)


def test_weekly_new_customers(nb):
    out = nb.weekly_new_customers(invoices_fixture(), "2011-01-01", "2011-05-01")
    assert out.name == "new_customers"
    # mua đầu: 1 -> 5/1 (tuần 3-9/1), 2 -> 10/1, 3 -> 15/1 (tuần 10-16/1), 4 -> 1/3; 5 trước start; 6 sau end
    assert {str(k): v for k, v in out.items()} == {
        "2011-01-03/2011-01-09": 1, "2011-01-10/2011-01-16": 2, "2011-02-28/2011-03-06": 1}
    assert list(out.index) == sorted(out.index)


def test_sample_size_known_values(nb):
    assert nb.sample_size_per_arm(0.10, 0.02) == 3841
    assert nb.sample_size_per_arm(0.50, 0.05) == 1565
    assert nb.sample_size_per_arm(0.02, 0.002) == 80682
    assert isinstance(nb.sample_size_per_arm(0.10, 0.02), int)


def test_sample_size_alpha_power_and_statsmodels(nb):
    base = nb.sample_size_per_arm(0.35, 0.05)
    assert nb.sample_size_per_arm(0.35, 0.05, power=0.9) > base
    assert nb.sample_size_per_arm(0.35, 0.05, alpha=0.01) > base
    # công thức gần với cách tính bằng effect size Cohen's h của statsmodels (lệch dưới 1%)
    h = proportion_effectsize(0.40, 0.35)
    ref = NormalIndPower().solve_power(h, alpha=0.05, power=0.8)
    assert abs(base - ref) / ref < 0.01


def test_weeks_needed(nb):
    assert nb.weeks_needed(3841, 1000) == 8
    assert nb.weeks_needed(3841, 1000, share=0.5) == 16
    assert nb.weeks_needed(1000, 1000, arms=3) == 3
    assert nb.weeks_needed(100, 1000) == 2
    assert nb.weeks_needed(100, 1000, min_weeks=1) == 1


def test_mde_for_weeks(nb):
    mde = nb.mde_for_weeks(0.10, 1000, 4)
    assert mde == pytest.approx(0.028156, abs=1e-4)
    available = math.floor(4 * 1000 / 2)
    assert nb.sample_size_per_arm(0.10, mde) <= available
    assert nb.sample_size_per_arm(0.10, mde - 2e-4) > available
    assert nb.mde_for_weeks(0.10, 1000, 16) < mde
    assert math.isnan(nb.mde_for_weeks(0.10, 1, 1))


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
def real_invoices(nb):
    raw = load_online_retail(ex.dataset("online-retail-ii") / "online_retail_II.xlsx")
    return nb.customer_invoices(raw), raw["invoice_date"].max()


def test_real_baseline_and_traffic(nb, real_invoices):
    invoices, end = real_invoices
    assert len(invoices) == 36969
    assert invoices["customer_id"].nunique() == 5878
    rate, n = nb.repeat_rate(invoices, 60, "2010-01-01", end)
    assert n == 4563
    assert rate == pytest.approx(0.35196, abs=1e-4)
    weekly = nb.weekly_new_customers(invoices, "2011-01-03", "2011-11-28")
    assert len(weekly) == 47 and weekly.sum() == 1488
    assert nb.sample_size_per_arm(rate, 0.05) == 1474
    assert nb.weeks_needed(1474, weekly.mean()) == 94
    assert nb.mde_for_weeks(rate, weekly.mean(), 4) == pytest.approx(0.24696, abs=1e-3)
