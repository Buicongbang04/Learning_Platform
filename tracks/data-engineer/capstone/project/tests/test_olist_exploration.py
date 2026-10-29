"""Test notebook khám phá Olist thật: notebooks/olist_exploration.ipynb.

    uv run pytest tracks/data-engineer/capstone/project/tests/test_olist_exploration.py -q -rs
    SOLUTION=1 uv run pytest tracks/data-engineer/capstone/project/tests/test_olist_exploration.py -q   # bản tham chiếu

Capstone là dự án của bạn nên test không fail khi bạn chưa làm tới: hàm còn `NotImplementedError`, biểu đồ
chưa vẽ, báo cáo còn TODO thì test tương ứng skip kèm lời nhắc (`-rs` để xem). Test trên dữ liệu nhỏ luôn
chạy được offline; test trên bộ thật skip khi chưa có `data/raw/olist_orders_dataset.csv`.
"""

import re
from pathlib import Path

import nbformat
import pandas as pd
import pytest

from testkit import ROOT, Exercise, use_solution

PROJECT = Path(__file__).resolve().parents[1]
NOTEBOOK = "olist_exploration.ipynb"
RAW = ROOT / "data" / "raw"
REAL_ORDERS = 99_441          # số đơn của bộ Olist thật trên Kaggle (bản giả lập có số đơn khác)


class Notebook(Exercise):
    """Capstone không có starter/solutions như bài tập: notebook nằm ở project/notebooks/,
    bản tham chiếu (SOLUTION=1) ở capstone/solutions/notebooks/."""

    def __init__(self):
        self.dir = PROJECT
        self.fixtures = PROJECT / "tests" / "fixtures"
        self.target = PROJECT.parent / "solutions" / "notebooks" if use_solution() else PROJECT / "notebooks"


ex = Notebook()


@pytest.fixture(scope="module")
def nb():
    return ex.notebook(NOTEBOOK)


def call(fn, *args, **kwargs):
    """Gọi hàm của notebook; hàm còn TODO thì skip thay vì fail."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        pytest.skip(f"Chưa làm: {fn.__name__}() trong project/notebooks/{NOTEBOOK} còn TODO")


# ---------- dữ liệu nhỏ dựng trong test ----------

def ts(value):
    return pd.Timestamp(value) if value else pd.NaT


def small_tables():
    orders = pd.DataFrame(
        [
            # giao 15h đúng ngày dự kiến: không trễ
            ("o1", "c1", "delivered", "2018-01-01 10:00", "2018-01-02 08:00", "2018-01-10 15:00", "2018-01-10"),
            # giao sau dự kiến 2 ngày lịch: trễ
            ("o2", "c2", "delivered", "2018-01-03 09:00", "2018-01-04 08:00", "2018-01-12 09:00", "2018-01-10"),
            # delivered nhưng thiếu ngày giao: không tính là đã giao
            ("o3", "c3", "delivered", "2018-01-05 09:00", "2018-01-06 08:00", None, "2018-01-20"),
            # huỷ: không item, không payment, không review
            ("o4", "c4", "canceled", "2018-01-06 09:00", None, None, "2018-01-25"),
            # giao hãng trước lúc mua: mốc thời gian vô lý
            ("o5", "c5", "shipped", "2018-02-01 09:00", "2018-01-31 08:00", None, "2018-02-20"),
        ],
        columns=["order_id", "customer_id", "order_status", "order_purchase_timestamp",
                 "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"],
    )
    for col in ["order_purchase_timestamp", "order_delivered_carrier_date",
                "order_delivered_customer_date", "order_estimated_delivery_date"]:
        orders[col] = pd.to_datetime(orders[col])
    orders.insert(4, "order_approved_at", orders["order_purchase_timestamp"])
    customers = pd.DataFrame({
        "customer_id": ["c1", "c2", "c3", "c4", "c5"],
        "customer_unique_id": ["u1", "u1", "u2", "u3", "u4"],   # u1 mua hai lần
        "customer_zip_code_prefix": ["01310", "01310", "20000", "20000", "30000"],
        "customer_city": ["sao paulo", "sao paulo", "rio", "rio", "bh"],
        "customer_state": ["SP", "SP", "RJ", "RJ", "MG"],
    })
    items = pd.DataFrame({
        "order_id": ["o1", "o1", "o2", "o3", "o5"],
        "order_item_id": [1, 2, 1, 1, 1],
        "product_id": ["p1", "p2", "p1", "p3", "p1"],
        "seller_id": ["s1", "s1", "s2", "s1", "s3"],
        "price": [10.0, 20.0, 100.0, 50.0, 1.0],
        "freight_value": [5.0, 5.0, 10.0, 5.0, 0.5],
    })
    payments = pd.DataFrame({
        "order_id": ["o1", "o1", "o2", "o3", "o5"],
        "payment_sequential": [1, 2, 1, 1, 1],
        "payment_type": ["credit_card", "voucher", "boleto", "credit_card", "credit_card"],
        "payment_installments": [3, 1, 1, 1, 2],
        "payment_value": [20.0, 20.0, 110.0, 55.0, 1.5],
    })
    reviews = pd.DataFrame({
        "review_id": ["r1", "r2", "r3", "r4"],
        "order_id": ["o1", "o1", "o2", "o3"],
        "review_score": [1, 5, 2, 4],
        "review_creation_date": pd.to_datetime(["2018-01-11", "2018-01-12", "2018-01-13", "2018-01-14"]),
        "review_answer_timestamp": pd.to_datetime(["2018-01-11 10:00", "2018-01-12 10:00",
                                                   "2018-01-13 10:00", "2018-01-14 10:00"]),
    })
    products = pd.DataFrame({"product_id": ["p1", "p2", "p3"],
                             "product_category_name": ["beleza_saude", "pc_gamer", None]})
    translation = pd.DataFrame({"product_category_name": ["beleza_saude"],
                                "product_category_name_english": ["health_beauty"]})
    sellers = pd.DataFrame({"seller_id": ["s1", "s2", "s3"], "seller_state": ["SP", "SP", "PR"]})
    return {"orders": orders, "customers": customers, "items": items, "payments": payments, "reviews": reviews,
            "products": products, "sellers": sellers, "translation": translation}


def by_id(df):
    return df.set_index("order_id")


# ---------- làm sạch ----------

def test_clean_orders_flags_and_delay(nb):
    tables = small_tables()
    before = tables["orders"].copy()
    out = by_id(call(nb.clean_orders, tables["orders"]))
    pd.testing.assert_frame_equal(tables["orders"], before)       # không sửa đầu vào
    assert len(out) == 5                                          # không xoá dòng nào
    assert out["is_delivered"].tolist() == [True, True, False, False, False]
    assert out.loc["o1", "delay_days"] == 0 and not out.loc["o1", "is_late"]    # đúng ngày hẹn, khác giờ
    assert out.loc["o2", "delay_days"] == 2 and out.loc["o2", "is_late"]
    assert pd.isna(out.loc["o3", "delay_days"]) and pd.isna(out.loc["o3", "is_late"])
    assert pd.isna(out.loc["o3", "delivery_days"])
    assert out.loc["o1", "delivery_days"] == pytest.approx(9 + 5 / 24)
    assert str(out["delay_days"].dtype) == "Int64" and str(out["is_late"].dtype) == "boolean"
    assert out["purchase_month"].tolist() == ["2018-01"] * 4 + ["2018-02"]
    assert out["bad_timeline"].tolist() == [False, False, False, False, True]


def test_dedup_reviews_keeps_latest_answer(nb):
    out = call(nb.dedup_reviews, small_tables()["reviews"])
    assert out["order_id"].is_unique and len(out) == 3
    assert by_id(out).loc["o1", "review_id"] == "r2" and by_id(out).loc["o1", "review_score"] == 5


def test_order_facts_one_row_per_order_money_not_multiplied(nb):
    tables = small_tables()
    facts = call(nb.build_order_facts, tables)
    assert list(facts.columns) == nb.FACT_COLUMNS
    assert facts["order_id"].is_unique and len(facts) == 5
    f = by_id(facts)
    # o1: 2 item x 2 payment, join thẳng sẽ thành 4 dòng và tiền gấp đôi
    assert (f.loc["o1", "n_items"], f.loc["o1", "items_value"], f.loc["o1", "freight_value"],
            f.loc["o1", "payment_value"]) == (2, 30.0, 10.0, 40.0)
    assert f.loc["o1", "review_score"] == 5 and f.loc["o1", "customer_unique_id"] == "u1"
    assert (f.loc["o4", "n_items"], f.loc["o4", "items_value"], f.loc["o4", "payment_value"]) == (0, 0.0, 0.0)
    assert pd.isna(f.loc["o4", "review_score"])
    assert facts["items_value"].sum() == pytest.approx(tables["items"]["price"].sum())
    assert str(facts["review_score"].dtype) == "Int64"


# ---------- phân tích trên dữ liệu nhỏ ----------

def small_facts(nb):
    return call(nb.build_order_facts, small_tables())


def test_review_by_delay_buckets(nb):
    out = call(nb.review_by_delay, small_facts(nb))
    assert list(out.index) == nb.DELAY_BUCKETS
    assert out.loc["đúng ngày", "orders"] == 1 and out.loc["đúng ngày", "avg_review"] == 5
    assert out.loc["trễ 1–7 ngày", "orders"] == 1 and out.loc["trễ 1–7 ngày", "low_review_share"] == 1
    assert out.loc["trễ > 7 ngày", "orders"] == 0


def test_late_share_by_state(nb):
    out = call(nb.late_share_by_state, small_facts(nb), min_orders=1)
    assert list(out.index) == ["SP"]                    # chỉ SP có đơn đã giao
    assert out.loc["SP", "delivered"] == 2 and out.loc["SP", "late_share"] == pytest.approx(0.5)
    assert call(nb.late_share_by_state, small_facts(nb), min_orders=3).empty


def test_payment_mix_counts_distinct_orders(nb):
    out = call(nb.payment_mix, small_tables()["payments"])
    assert out.index[0] == "credit_card"
    assert out.loc["credit_card", "orders"] == 3 and out.loc["credit_card", "order_share"] == pytest.approx(0.75)
    assert out.loc["boleto", "value_share"] == pytest.approx(110 / 206.5)


def test_seller_concentration(nb):
    items = small_tables()["items"]                   # s2 = 100, s1 = 80, s3 = 1
    assert call(nb.seller_concentration, items) == pytest.approx(100 / 181)              # ceil(0,3) = 1 seller
    assert call(nb.seller_concentration, items, top=0.5) == pytest.approx(180 / 181)     # ceil(1,5) = 2 seller


def test_category_revenue_translation_fallbacks(nb):
    t = small_tables()
    out = call(nb.category_revenue, t["items"], t["products"], t["translation"])
    assert out.to_dict() == {"health_beauty": 111.0, "unknown": 50.0, "pc_gamer": 20.0}
    assert list(out.index) == ["health_beauty", "unknown", "pc_gamer"]


def test_repeat_customer_rate_ignores_canceled(nb):
    # u1 có 2 đơn; u3 chỉ có đơn huỷ nên không tính
    assert call(nb.repeat_customer_rate, small_facts(nb)) == pytest.approx(1 / 3)


def test_insights_on_small(nb):
    t = small_tables()
    got = call(nb.insights, small_facts(nb), t, min_orders=1)
    assert (got["orders"], got["delivered"]) == (5, 2)
    assert got["late_share"] == pytest.approx(0.5)
    assert (got["avg_review_on_time"], got["avg_review_late"]) == (5, 2)
    assert (got["low_review_share_on_time"], got["low_review_share_late"]) == (0, 1)
    assert (got["worst_state"], got["top_payment_type"], got["top_category"]) == ("SP", "credit_card", "health_beauty")
    assert got["card_installments_share"] == pytest.approx(2 / 3)
    assert got["repeat_customer_rate"] == pytest.approx(1 / 3)


def test_write_clean_overwrites(nb, tmp_path):
    facts = small_facts(nb)
    first = call(nb.write_clean, facts, tmp_path / "olist")
    second = nb.write_clean(facts, tmp_path / "olist")
    assert first == second and first.name == "order_facts.parquet"
    assert [p.name for p in (tmp_path / "olist").iterdir()] == ["order_facts.parquet"]   # không sót tệp tạm
    back = pd.read_parquet(first)
    assert len(back) == 5 and str(back["review_score"].dtype) == "Int64"


# ---------- bộ Olist thật ----------

_CACHE = {}


def real(nb):
    """Nạp bộ thật và tính một lần (~1 giây) cho mọi test dữ liệu thật."""
    if not (RAW / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa có Olist thật. Chạy: uv run python data/download_olist.py")
    if "real" not in _CACHE:
        tables = nb.load_olist(RAW)
        if len(tables["orders"]) != REAL_ORDERS:
            pytest.skip("data/raw/ đang là bộ giả lập; tải bộ thật: uv run python data/download_olist.py")
        facts = call(nb.build_order_facts, tables)
        _CACHE["real"] = tables, facts
    return _CACHE["real"]


def real_insights(nb):
    tables, facts = real(nb)
    if "insights" not in _CACHE:
        _CACHE["insights"] = call(nb.insights, facts, tables)
    return _CACHE["insights"]


def test_real_load_keeps_zip_as_text(nb):
    tables, _ = real(nb)
    zips = tables["customers"]["customer_zip_code_prefix"]
    assert zips.str.len().eq(5).all() and zips.str.startswith("0").any()


def test_real_clean_facts_quality(nb):
    tables, facts = real(nb)
    assert facts["order_id"].is_unique and len(facts) == REAL_ORDERS
    assert facts["items_value"].sum() == pytest.approx(13_591_643.70, abs=0.01)
    assert facts["items_value"].sum() == pytest.approx(tables["items"]["price"].sum())
    assert facts["review_score"].dropna().between(1, 5).all()
    assert facts["review_score"].notna().sum() == 98_673            # 768 đơn không có review
    assert (facts["delay_days"].notna() == facts["is_delivered"]).all()
    assert facts["bad_timeline"].sum() == 189
    assert (facts.loc[facts["is_delivered"], "delivery_days"] > 0).all()


def test_real_delivery_and_review(nb):
    got = real_insights(nb)
    assert (got["orders"], got["delivered"]) == (99_441, 96_470)     # 8 đơn delivered thiếu ngày giao
    assert got["late_share"] == pytest.approx(0.0677, abs=0.0005)
    assert got["median_delivery_days"] == pytest.approx(10.22, abs=0.01)
    # trễ hạn kéo điểm review từ 4,29 xuống 2,27; 62% đơn trễ bị 1–2 sao
    assert got["avg_review_on_time"] == pytest.approx(4.290, abs=0.005)
    assert got["avg_review_late"] == pytest.approx(2.270, abs=0.005)
    assert got["low_review_share_on_time"] == pytest.approx(0.0927, abs=0.0005)
    assert got["low_review_share_late"] == pytest.approx(0.6242, abs=0.0005)


def test_real_review_by_delay_monotonic(nb):
    _, facts = real(nb)
    out = call(nb.review_by_delay, facts)
    assert out["orders"].tolist() == [75_744, 12_419, 1_280, 3_600, 2_781]
    assert out["avg_review"].is_monotonic_decreasing
    assert out.loc["trễ > 7 ngày", "avg_review"] == pytest.approx(1.696, abs=0.005)


def test_real_late_by_state(nb):
    got = real_insights(nb)
    assert got["worst_state"] == "AL"                                 # Alagoas, Đông Bắc, xa São Paulo
    assert got["worst_state_late_share"] == pytest.approx(0.2141, abs=0.0005)


def test_real_payments_sellers_categories_customers(nb):
    got = real_insights(nb)
    assert got["top_payment_type"] == "credit_card"
    assert got["top_payment_order_share"] == pytest.approx(0.7694, abs=0.0005)
    assert got["card_installments_share"] == pytest.approx(0.6685, abs=0.0005)
    assert got["top10_seller_gmv_share"] == pytest.approx(0.6756, abs=0.0005)   # 310/3 095 seller
    assert got["top_category"] == "health_beauty"
    assert got["top_category_revenue"] == pytest.approx(1_258_681.34, abs=0.01)
    assert got["repeat_customer_rate"] == pytest.approx(0.0304, abs=0.0005)


# ---------- biểu đồ và báo cáo ----------

def test_notebook_draws_charts():
    book = nbformat.read(ex.path(NOTEBOOK), as_version=4)
    plots = [c for c in book.cells if c.cell_type == "code" and "explore" in c.metadata.get("tags", [])
             and re.search(r"plt\.|\.plot\(|\.plot\.|\.bar\(|\.barh\(|\.hist\(", "\n".join(
                 line for line in c.source.splitlines() if not line.lstrip().startswith("#")))]
    if not plots:
        pytest.skip("Chưa vẽ biểu đồ nào trong các cell explore ở mục 4")
    assert len(plots) >= 2, "Cần ít nhất 2 cell explore vẽ biểu đồ"


def test_report_sections_and_numbers():
    text = ex.read("report.md")
    if "TODO" in text:
        pytest.skip("Chưa viết xong project/notebooks/report.md (còn TODO)")
    for heading in ("## Bộ dữ liệu", "## Làm sạch", "## Insight", "## Giới hạn"):
        assert heading in text
    insight = text.split("## Insight", 1)[1].split("\n## ", 1)[0]
    assert len(re.findall(r"\d[\d.,]*", insight)) >= 3, "Mục Insight cần số liệu cụ thể"
