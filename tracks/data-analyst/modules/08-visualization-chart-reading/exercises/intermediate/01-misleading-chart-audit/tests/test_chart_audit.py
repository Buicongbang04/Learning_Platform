import os

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from testkit import Exercise  # noqa: E402

ex = Exercise(__file__)

CODES = {"truncated_bar_axis", "dual_axis", "pie_too_many_slices", "unsorted_bars", "missing_axis_label"}


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("chart_audit.ipynb")


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def labelled(ax, x="nhóm", y="giá trị"):
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    return ax


def test_clean_sorted_bar_has_no_issue(nb):
    fig, ax = plt.subplots()
    ax.bar(["SP", "RJ", "MG"], [40, 13, 11])
    labelled(ax, "bang", "nghìn đơn")
    assert nb.audit_chart(fig) == set()


def test_truncated_bar_axis(nb):
    fig, ax = plt.subplots()
    ax.bar(["T6", "T4", "CN"], [4690, 4550, 4229])
    ax.set_ylim(4000, 4800)
    labelled(ax, "thứ", "lượt/ngày")
    assert nb.audit_chart(fig) == {"truncated_bar_axis"}


def test_truncated_horizontal_bar(nb):
    fig, ax = plt.subplots()
    ax.barh(["a", "b", "c"], [3, 2, 1])          # trục giá trị là trục x
    ax.set_xlim(0.5, 3.5)
    labelled(ax, "giá trị", "nhóm")
    assert nb.audit_chart(fig) == {"truncated_bar_axis"}


def test_line_not_from_zero_is_fine(nb):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4], [102, 98, 105, 110])  # line mã hoá bằng vị trí, được phép không từ 0
    ax.set_ylim(90, 115)
    labelled(ax, "tháng", "chỉ số")
    assert nb.audit_chart(fig) == set()


def test_dual_axis(nb):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [10, 20, 30])
    labelled(ax, "tháng", "lượt thuê")
    ax2 = ax.twinx()
    ax2.plot([1, 2, 3], [0.2, 0.5, 0.4], color="C1")
    ax2.set_ylabel("nhiệt độ")
    assert nb.audit_chart(fig) == {"dual_axis"}


def test_side_by_side_panels_are_not_dual_axis(nb):
    fig, (a, b) = plt.subplots(1, 2)
    for ax in (a, b):
        ax.plot([1, 2, 3], [1, 4, 9])
        labelled(ax, "x", "y")
    assert nb.audit_chart(fig) == set()


def test_pie_too_many_slices(nb):
    fig, ax = plt.subplots()
    ax.pie([30, 20, 12, 10, 9, 8, 6, 5], labels=list("abcdefgh"))
    assert nb.audit_chart(fig) == {"pie_too_many_slices"}


def test_pie_with_few_slices_is_fine(nb):
    fig, ax = plt.subplots()
    ax.pie([81, 19], labels=["registered", "casual"])   # pie không có trục: không đòi nhãn trục
    assert nb.audit_chart(fig) == set()


def test_pie_with_six_slices_is_fine(nb):
    fig, ax = plt.subplots()
    ax.pie([6, 5, 4, 3, 2, 1])
    assert nb.audit_chart(fig) == set()


def test_unsorted_category_bars(nb):
    fig, ax = plt.subplots()
    ax.bar(["boleto", "credit_card", "debit_card", "voucher"], [19784, 76795, 1529, 5775])
    labelled(ax, "phương thức", "số giao dịch")
    assert nb.audit_chart(fig) == {"unsorted_bars"}


def test_ascending_category_bars_count_as_sorted(nb):
    fig, ax = plt.subplots()
    ax.barh(["c", "b", "a"], [1, 2, 3])          # barh tăng dần từ dưới lên = lớn nhất ở trên cùng
    labelled(ax, "giá trị", "nhóm")
    assert nb.audit_chart(fig) == set()


def test_unsorted_pandas_bar(nb):
    fig, ax = plt.subplots()
    pd.Series([2, 9, 4], index=["x", "y", "z"]).plot.bar(ax=ax)
    labelled(ax, "nhóm", "giá trị")
    assert nb.audit_chart(fig) == {"unsorted_bars"}


def test_numeric_x_bars_keep_their_order(nb):
    fig, ax = plt.subplots()
    ax.bar(range(24), [abs(12 - h) for h in range(24)])   # giờ trong ngày: trục số, giữ thứ tự tự nhiên
    labelled(ax, "giờ", "lượt")
    assert nb.audit_chart(fig) == set()


def test_date_x_bars_are_not_categories(nb):
    fig, ax = plt.subplots()
    ax.bar(pd.date_range("2011-01-01", periods=4, freq="MS"), [5, 9, 3, 7], width=20)
    labelled(ax, "tháng", "doanh thu")
    assert nb.audit_chart(fig) == set()


def test_missing_axis_label(nb):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [3, 1, 2])
    ax.set_xlabel("tháng")
    assert nb.audit_chart(fig) == {"missing_axis_label"}


def test_several_issues_at_once(nb):
    fig, (a, b) = plt.subplots(1, 2)
    a.bar(["x", "y", "z"], [5, 9, 7])
    a.set_ylim(4, 10)
    b.pie(range(1, 9))
    assert nb.audit_chart(fig) == {"truncated_bar_axis", "unsorted_bars", "missing_axis_label", "pie_too_many_slices"}


def test_audit_returns_known_codes_only(nb):
    fig, ax = plt.subplots()
    ax.bar(["x", "y"], [1, 2])
    out = nb.audit_chart(fig)
    assert isinstance(out, set) and out <= CODES


def test_honest_bar_is_clean_and_sorted(nb):
    s = pd.Series([19784, 76795, 1529, 5775], index=pd.Index(["boleto", "credit_card", "debit_card", "voucher"],
                  name="phương thức"), name="số giao dịch")
    before = s.copy()
    fig, ax = plt.subplots()
    out = nb.honest_bar(ax, s)
    assert out is ax
    assert nb.audit_chart(out.figure) == set()
    heights = [p.get_height() for p in ax.containers[0]]
    assert heights == [76795, 19784, 5775, 1529]
    assert [t.get_text() for t in ax.get_xticklabels()] == ["credit_card", "boleto", "voucher", "debit_card"]
    assert ax.get_ylim()[0] == 0
    assert ax.get_xlabel() == "phương thức" and ax.get_ylabel() == "số giao dịch"
    pd.testing.assert_series_equal(s, before)


def test_honest_bar_needs_names_for_labels(nb):
    fig, ax = plt.subplots()
    with pytest.raises(ValueError):
        nb.honest_bar(ax, pd.Series([1, 2], index=["a", "b"]))
