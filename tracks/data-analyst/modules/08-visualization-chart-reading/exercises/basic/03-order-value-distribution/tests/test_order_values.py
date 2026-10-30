import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("order_values.ipynb")


def test_invoice_totals_excludes_cancel_and_negative(nb):
    tx = pd.DataFrame({"Invoice": ["1", "1", "C2", "3", "4"], "Quantity": [2, 1, -1, 5, 3], "Price": [1.5, 2.0, 9.0, 0.0, 1.0]})
    assert nb.invoice_totals(tx).to_dict() == {"1": 5.0, "4": 3.0}


def test_invoice_totals_drops_bad_lines_but_keeps_invoice(nb):
    # Excel đọc mã hoá đơn thành int, mã có chữ (C..., A...) thành str: chuẩn hoá về str
    tx = pd.DataFrame({
        "Invoice": [489434, 489434, 489434, "C489449", "A506401", 489435],
        "Quantity": [12, -3, 4, 10, 1, 1],
        "Price": [2.0, 2.0, 0.5, 3.0, -100.0, 0.0],
    })
    out = nb.invoice_totals(tx)
    assert out.to_dict() == {"489434": 26.0}
    assert out.index.name == "Invoice"


def test_invoice_totals_does_not_mutate_input(nb):
    tx = pd.DataFrame({"Invoice": [1, 2], "Quantity": [1, 2], "Price": [3.0, 4.0]})
    before = tx.copy()
    nb.invoice_totals(tx)
    pd.testing.assert_frame_equal(tx, before)


def test_summary_stats(nb):
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0])
    out = nb.summary_stats(s)
    assert set(out) == {"mean", "median", "p90", "p99", "skew"}
    assert out["mean"] == pytest.approx(22.0)
    assert out["median"] == pytest.approx(3.0)
    assert out["p90"] == pytest.approx(61.6)                     # nội suy tuyến tính, mặc định của pandas
    assert out["p99"] == pytest.approx(96.16)
    assert out["skew"] == pytest.approx(s.skew())
    assert out["skew"] > 2
    assert all(isinstance(v, float) for v in out.values())


def test_summary_stats_symmetric_has_zero_skew(nb):
    out = nb.summary_stats(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert out["mean"] == pytest.approx(out["median"])
    assert out["skew"] == pytest.approx(0.0)


def test_log_bins_powers_of_ten(nb):
    edges = nb.log_bins(pd.Series([1.0, 10.0, 100.0, 1000.0]), 3)
    assert isinstance(edges, np.ndarray)
    assert edges == pytest.approx([1.0, 10.0, 100.0, 1000.0])


def test_log_bins_equal_width_in_log_space(nb):
    s = pd.Series([0.19, 3.5, 42.0, 300.0, 49_844.99])
    edges = nb.log_bins(s, 8)
    assert len(edges) == 9
    assert np.allclose(np.diff(np.log10(edges)), np.log10(s.max() / s.min()) / 8)
    assert edges[0] <= s.min() and edges[-1] >= s.max()             # np.histogram không bỏ sót điểm nào
    counts, _ = np.histogram(s, bins=edges)
    assert counts.sum() == len(s)


def test_log_bins_rejects_non_positive(nb):
    with pytest.raises(ValueError):
        nb.log_bins(pd.Series([0.0, 1.0, 10.0]), 5)


@pytest.fixture(scope="module")
def real_tx():
    path = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    return pd.read_excel(path, sheet_name="Year 2009-2010")      # xlsx: đọc một lần cho cả module


def test_real_invoice_totals(nb, real_tx):
    real_totals = nb.invoice_totals(real_tx)
    assert len(real_totals) == 20_951
    assert real_totals.sum() == pytest.approx(10_305_892.02, abs=1)
    assert real_totals.min() > 0


def test_real_summary_stats(nb, real_tx):
    out = nb.summary_stats(nb.invoice_totals(real_tx))
    assert out["median"] == pytest.approx(300.84, abs=0.01)
    assert out["p90"] == pytest.approx(920.70, abs=0.01)
    assert out["p99"] == pytest.approx(4098.96, abs=0.01)
    assert out["skew"] == pytest.approx(17.64, abs=0.05)


def test_real_log_bins(nb, real_tx):
    real_totals = nb.invoice_totals(real_tx)
    edges = nb.log_bins(real_totals, 40)
    counts, _ = np.histogram(real_totals, bins=edges)
    assert counts.sum() == len(real_totals)
    assert edges[0] == pytest.approx(0.19) and edges[-1] == pytest.approx(49_844.99)
