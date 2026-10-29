import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("peeking.ipynb")


def test_single_look_keeps_nominal_alpha(nb):
    assert 0.04 <= nb.peeking_fpr(n_per_group=200, n_looks=1, n_sims=4000) <= 0.06


def test_ten_looks_inflate_false_positives(nb):
    fpr = nb.peeking_fpr(n_per_group=200, n_looks=10, n_sims=4000)
    assert fpr > 0.12


def test_more_looks_more_false_positives(nb):
    rates = [nb.peeking_fpr(n_per_group=200, n_looks=k, n_sims=4000) for k in (1, 3, 10)]
    assert rates == sorted(rates)


def test_peeking_is_reproducible(nb):
    assert nb.peeking_fpr(100, 5, 1000, seed=3) == nb.peeking_fpr(100, 5, 1000, seed=3)


def test_obf_with_huge_constant_never_rejects(nb):
    assert nb.obf_fpr(10.0, n_per_group=200, n_looks=5, n_sims=2000) == 0.0


def test_obf_with_1_96_is_too_liberal(nb):
    assert nb.obf_fpr(1.96, n_per_group=200, n_looks=5, n_sims=4000) > 0.05


def test_calibrated_obf_constant_matches_textbook(nb):
    c = nb.calibrate_obf_constant(n_looks=5)
    assert 1.99 <= c <= 2.09                    # giá trị trong sách: 2.040
    assert 0.04 <= nb.obf_fpr(c, n_per_group=100, n_looks=5, n_sims=20000, seed=1) <= 0.06
