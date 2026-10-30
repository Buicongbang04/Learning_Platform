import hashlib
import math
import os
import re
import tempfile
import uuid
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportions_ztest

from testkit import Exercise

ex = Exercise(__file__)
BRIEF_HEADINGS = ["## Câu hỏi và quyết định", "## Đối tượng và chia nhóm", "## Metric chính và guardrail",
                  "## Sample size và thời lượng", "## Kiểm tra trước khi đọc kết quả", "## Quy tắc quyết định",
                  "## Readout chạy thử (A/A)", "## Rủi ro và giới hạn"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("experiment_brief.ipynb")


def invoices_fixture():
    t = pd.Timestamp
    return pd.DataFrame({
        "customer_id": [3.0, 1.0, 1.0, 2.0, 4.0, 5.0, 5.0, 6.0],
        "invoice": ["a", "b", "c", "d", "e", "f", "g", "h"],
        "invoice_date": [
            t("2011-08-31 23:00"),  # 3: hoạt động (sát as_of)
            t("2011-06-10 10:00"),  # 1: hoạt động
            t("2011-09-05 10:00"),  # 1: mua trong cửa sổ
            t("2011-06-02 10:00"),  # 2: ngoài 90 ngày (as_of - 90 ngày = 2011-06-03)
            t("2011-09-01 00:00"),  # 4: đúng lúc as_of -> thuộc giai đoạn thí nghiệm, không phải lịch sử
            t("2011-07-01 10:00"),  # 5: hoạt động
            t("2011-10-01 00:00"),  # 5: đúng lúc kết thúc cửa sổ 30 ngày -> ngoài
            t("2011-09-10 10:00"),  # 6: không có trong danh sách khách
        ],
        "revenue": [50.0, 20.0, 30.0, 40.0, 60.0, 70.0, 80.0, 90.0],
    })


def test_eligible_customers(nb):
    inv = invoices_fixture()
    before = inv.copy()
    out = nb.eligible_customers(inv, "2011-09-01")
    assert isinstance(out, pd.Index) and out.name == "customer_id"
    assert list(out) == [1, 3, 5]
    assert list(nb.eligible_customers(inv, "2011-09-01", lookback_days=91)) == [1, 2, 3, 5]
    pd.testing.assert_frame_equal(inv, before)


def test_outcome_window(nb):
    inv = invoices_fixture()
    before = inv.copy()
    out = nb.outcome_window(inv, pd.Index([5.0, 1.0, 3.0]), "2011-09-01", 30)
    assert list(out.index) == [5, 1, 3]
    assert list(out.columns) == ["purchased", "revenue"]
    assert out["purchased"].dtype == bool
    assert out["purchased"].tolist() == [False, True, False]
    assert out["revenue"].tolist() == pytest.approx([0.0, 30.0, 0.0])
    longer = nb.outcome_window(inv, [5.0, 1.0, 3.0], "2011-09-01", 31)
    assert longer["revenue"].tolist() == pytest.approx([80.0, 30.0, 0.0])
    pd.testing.assert_frame_equal(inv, before)


def expected_arm(cid, salt, share=0.5):
    bucket = int(hashlib.sha256(f"{salt}:{int(cid)}".encode("utf-8")).hexdigest()[:8], 16) % 10_000
    return "treatment" if bucket < round(share * 10_000) else "control"


def test_assign_arm_rule_and_stability(nb):
    ids = pd.Index([12346.0, 12347.0, 13085.0, 18287.0, 14646.0, 17850.0], name="customer_id")
    out = nb.assign_arm(ids, "exp-1")
    assert out.name == "arm"
    assert list(out.index) == list(ids)
    assert out.tolist() == [expected_arm(c, "exp-1") for c in ids]
    shuffled = nb.assign_arm(ids[::-1], "exp-1")
    assert shuffled.loc[ids].tolist() == out.tolist()  # không phụ thuộc thứ tự
    tenth = nb.assign_arm(ids, "exp-1", treatment_share=0.1)
    assert tenth.tolist() == [expected_arm(c, "exp-1", 0.1) for c in ids]


def test_assign_arm_share_and_salt(nb):
    ids = pd.Index(range(10_000, 30_000))
    a = nb.assign_arm(ids, "exp-a")
    assert set(a.unique()) == {"treatment", "control"}
    assert (a == "treatment").mean() == pytest.approx(0.5, abs=0.015)
    assert (nb.assign_arm(ids, "exp-a", treatment_share=0.2) == "treatment").mean() == pytest.approx(0.2, abs=0.015)
    same = (a == nb.assign_arm(ids, "exp-b")).mean()
    assert same == pytest.approx(0.5, abs=0.03)  # đổi salt thì chia lại độc lập


def test_mean_sample_size(nb):
    assert nb.mean_sample_size(1.0, 0.1) == 1570
    assert isinstance(nb.mean_sample_size(1.0, 0.1), int)
    ref = NormalIndPower().solve_power(0.25, alpha=0.05, power=0.8)
    assert nb.mean_sample_size(40.0, 10.0) == math.ceil(ref)
    assert nb.mean_sample_size(80.0, 10.0) == pytest.approx(4 * nb.mean_sample_size(40.0, 10.0), rel=0.01)
    assert nb.mean_sample_size(1.0, 0.1, power=0.9) > 1570


def outcome_fixture():
    rng = np.random.default_rng(3)
    n = 400
    idx = pd.Index(range(1000, 1000 + n), name="customer_id")
    bought = rng.random(n) < 0.35
    revenue = np.where(bought, rng.lognormal(5, 1.2, n), 0.0)
    revenue[7] = 50_000.0  # một khách sỉ
    arm = pd.Series(np.where(rng.random(n) < 0.5, "treatment", "control"), index=idx, name="arm")
    return pd.DataFrame({"purchased": bought, "revenue": revenue}, index=idx), arm


def test_readout_against_libraries(nb):
    outcome, arm = outcome_fixture()
    before = outcome.copy()
    out = nb.readout(outcome, arm)
    assert list(out.index) == ["purchased", "revenue"]
    assert list(out.columns) == ["control", "treatment", "diff", "ci_low", "ci_high", "p"]
    t, c = outcome[arm == "treatment"], outcome[arm == "control"]
    pt, pc = t.purchased.mean(), c.purchased.mean()
    assert out.loc["purchased", "diff"] == pytest.approx(pt - pc)
    se = math.sqrt(pt * (1 - pt) / len(t) + pc * (1 - pc) / len(c))
    assert out.loc["purchased", "ci_low"] == pytest.approx(pt - pc - 1.959964 * se, abs=1e-6)
    _, p = proportions_ztest([t.purchased.sum(), c.purchased.sum()], [len(t), len(c)])
    assert out.loc["purchased", "p"] == pytest.approx(p)
    ref = stats.ttest_ind(t.revenue, c.revenue, equal_var=False)
    ci = ref.confidence_interval()
    assert out.loc["revenue", "treatment"] == pytest.approx(t.revenue.mean())
    assert out.loc["revenue", "p"] == pytest.approx(ref.pvalue)
    assert out.loc["revenue", "ci_low"] == pytest.approx(ci.low)
    assert out.loc["revenue", "ci_high"] == pytest.approx(ci.high)
    pd.testing.assert_frame_equal(outcome, before)


def test_readout_cap_and_alpha(nb):
    outcome, arm = outcome_fixture()
    capped = nb.readout(outcome, arm, cap=1000.0)
    t, c = outcome[arm == "treatment"], outcome[arm == "control"]
    ref = stats.ttest_ind(t.revenue.clip(upper=1000), c.revenue.clip(upper=1000), equal_var=False)
    assert capped.loc["revenue", "p"] == pytest.approx(ref.pvalue)
    assert capped.loc["revenue", "control"] <= 1000
    assert capped.loc["purchased", "p"] == pytest.approx(nb.readout(outcome, arm).loc["purchased", "p"])
    wide = nb.readout(outcome, arm, alpha=0.01)
    assert wide.loc["purchased", "ci_low"] < nb.readout(outcome, arm).loc["purchased", "ci_low"]


def test_aa_false_positive_rate(nb):
    outcome, _ = outcome_fixture()
    salts = [f"s{k}" for k in range(40)]
    rate = nb.aa_false_positive_rate(outcome, salts)
    hits = [nb.readout(outcome, nb.assign_arm(outcome.index, s)).loc["purchased", "p"] < 0.05 for s in salts]
    assert rate == pytest.approx(np.mean(hits))
    rev = nb.aa_false_positive_rate(outcome, salts, metric="revenue", cap=1000.0, alpha=0.5)
    hits = [nb.readout(outcome, nb.assign_arm(outcome.index, s), cap=1000.0).loc["revenue", "p"] < 0.5 for s in salts]
    assert rev == pytest.approx(np.mean(hits))


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
    return nb.customer_invoices(raw)  # hàm viết sẵn: fixture không gọi hàm TODO để starter chỉ FAIL, không ERROR


def real_outcome(nb, invoices):
    eligible = nb.eligible_customers(invoices, "2011-09-01")
    return eligible, nb.outcome_window(invoices, eligible, "2011-09-01", 30)


def test_real_audience_and_baseline(nb, real_invoices):
    eligible, outcome = real_outcome(nb, real_invoices)
    assert len(eligible) == 1923
    assert outcome["purchased"].mean() == pytest.approx(0.37857, abs=1e-4)
    assert outcome["revenue"].std() == pytest.approx(2332.49, abs=0.05)
    assert outcome["revenue"].quantile(0.99) == pytest.approx(3673.55, abs=0.05)


def test_real_assignment_and_aa(nb, real_invoices):
    eligible, outcome = real_outcome(nb, real_invoices)
    arm = nb.assign_arm(eligible, "welcome-voucher-2011")
    assert (arm == "treatment").sum() == 958
    res = nb.readout(outcome, arm)
    assert res.loc["purchased", "p"] == pytest.approx(0.8748, abs=1e-3)
    assert res.loc["revenue", "diff"] == pytest.approx(-186.34, abs=0.01)  # một khách sỉ rơi vào control
    capped = nb.readout(outcome, arm, cap=outcome["revenue"].quantile(0.99))
    assert capped.loc["revenue", "diff"] == pytest.approx(-5.77, abs=0.01)
    salts = [f"aa-{k}" for k in range(200)]
    assert nb.aa_false_positive_rate(outcome, salts) == pytest.approx(0.055)


def test_brief_written():
    brief = ex.read("BRIEF.md")
    assert "TODO" not in brief, "Còn dòng TODO trong BRIEF.md"
    words = len(brief.split())
    assert 400 <= words <= 1000, f"Brief 400-1 000 từ, hiện có {words}"
    assert brief.strip().splitlines()[0].startswith("# "), "Dòng đầu là tên thí nghiệm (# ...)"
    for heading in BRIEF_HEADINGS:
        assert heading in brief, f"Thiếu mục {heading}"
    plan = brief.split("## Sample size và thời lượng")[1].split("\n## ")[0]
    assert re.search(r"\d", plan), "Mục Sample size phải có con số (baseline, MDE, số người mỗi nhóm)"
