import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

STEPS = ["purchased", "approved", "carrier", "delivered"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("simpson_funnel.ipynb")


def admissions(rows):
    return pd.DataFrame(rows, columns=["dept", "gender", "applied", "admitted"])


# Nữ có tỉ lệ cao hơn ở CẢ HAI khoa, nhưng nộp chủ yếu vào khoa khó (Y) nên tỉ lệ gộp thấp hơn
FLIP = admissions([
    ("X", "men", 80, 60), ("X", "women", 20, 16),
    ("Y", "men", 20, 4), ("Y", "women", 80, 20),
])
# Cùng cơ cấu nộp hồ sơ: gộp và theo khoa cùng chiều (nữ cao hơn)
NO_FLIP = admissions([
    ("X", "men", 50, 30), ("X", "women", 50, 35),
    ("Y", "men", 50, 10), ("Y", "women", 50, 12),
])


def test_admit_rate_pooled(nb):
    out = nb.admit_rate(FLIP, ["gender"])
    assert out.to_dict() == pytest.approx({"men": 64 / 100, "women": 36 / 100})


def test_admit_rate_by_dept_and_gender(nb):
    out = nb.admit_rate(FLIP, ["dept", "gender"])
    assert out.loc[("X", "women")] == pytest.approx(0.8)
    assert out.loc[("Y", "men")] == pytest.approx(0.2)
    assert len(out) == 4


def test_admit_rate_sums_counts_not_rates(nb):
    # hai dòng cùng nhóm: tỉ lệ gộp = tổng admitted / tổng applied, không phải trung bình hai tỉ lệ
    df = admissions([("X", "men", 10, 9), ("X", "men", 90, 9)])
    assert nb.admit_rate(df, ["gender"])["men"] == pytest.approx(18 / 100)


def test_admit_rate_does_not_mutate_input(nb):
    df = FLIP.copy()
    nb.admit_rate(df, ["dept", "gender"])
    pd.testing.assert_frame_equal(df, FLIP)


def test_simpson_flip_true(nb):
    assert nb.simpson_flip(FLIP) is True


def test_simpson_flip_false_when_same_direction(nb):
    assert nb.simpson_flip(NO_FLIP) is False


def test_simpson_flip_false_when_gap_only_from_mix_but_same_sign(nb):
    # Nam cao hơn ở cả gộp lẫn từng khoa: không đảo chiều dù cơ cấu khác nhau
    df = admissions([
        ("X", "men", 80, 64), ("X", "women", 20, 14),
        ("Y", "men", 20, 6), ("Y", "women", 80, 20),
    ])
    assert nb.simpson_flip(df) is False


def test_berkeley_constant(nb):
    b = nb.BERKELEY
    assert set(b.columns) >= {"dept", "gender", "applied", "admitted"}
    assert sorted(b.dept.unique()) == list("ABCDEF")
    totals = b.groupby("gender")[["applied", "admitted"]].sum()
    assert totals.loc["men"].tolist() == [2691, 1198]
    assert totals.loc["women"].tolist() == [1835, 557]
    a = b.set_index(["dept", "gender"])
    assert a.loc[("A", "women"), ["applied", "admitted"]].tolist() == [108, 89]
    assert a.loc[("F", "men"), ["applied", "admitted"]].tolist() == [373, 22]


def test_berkeley_is_a_simpson_flip(nb):
    pooled = nb.admit_rate(nb.BERKELEY, ["gender"])
    assert pooled["men"] == pytest.approx(0.4452, abs=1e-4)
    assert pooled["women"] == pytest.approx(0.3035, abs=1e-4)
    by_dept = nb.admit_rate(nb.BERKELEY, ["dept", "gender"]).unstack()
    assert (by_dept["women"] > by_dept["men"]).sum() == 4
    assert nb.simpson_flip(nb.BERKELEY) is True


def orders_fixture():
    t = "2018-01-0{} 10:00"
    return pd.DataFrame({
        "order_id": list("abcdef"),
        "order_purchase_timestamp": [t.format(i) for i in range(1, 7)],
        "order_approved_at": [t.format(1), t.format(2), t.format(3), t.format(4), None, None],
        "order_delivered_carrier_date": [t.format(2), t.format(3), None, None, None, t.format(7)],
        "order_delivered_customer_date": [t.format(5), None, None, None, None, t.format(9)],
    })


def test_order_funnel_counts_non_null(nb):
    out = nb.order_funnel(orders_fixture())
    assert list(out.index) == STEPS
    # đơn f thiếu approved nhưng vẫn có carrier/delivered: đếm từng cột độc lập như dữ liệu ghi nhận
    assert out.tolist() == [6, 4, 3, 2]


def test_order_funnel_does_not_mutate_input(nb):
    o = orders_fixture()
    before = o.copy()
    nb.order_funnel(o)
    pd.testing.assert_frame_equal(o, before)


def test_step_conversion(nb):
    funnel = pd.Series([1000, 800, 600, 540], index=STEPS)
    out = nb.step_conversion(funnel)
    assert list(out.index) == STEPS
    assert out.tolist() == pytest.approx([1.0, 0.8, 0.75, 0.9])
    assert not np.isnan(out).any()


@pytest.fixture(scope="module")
def real_orders():
    path = ROOT / "data" / "raw" / "olist_orders_dataset.csv"
    if not path.exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    return pd.read_csv(path)


def test_real_order_funnel(nb, real_orders):
    funnel = nb.order_funnel(real_orders)
    assert funnel.tolist() == [99441, 99281, 97658, 96476]
    conv = nb.step_conversion(funnel)
    assert conv["carrier"] == pytest.approx(0.98365, abs=1e-5)
    assert conv.idxmin() == "carrier"
