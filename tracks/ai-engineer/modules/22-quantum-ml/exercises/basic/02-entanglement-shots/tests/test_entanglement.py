import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def ent():
    return ex.module("entanglement.py")


def basis(bits: str) -> np.ndarray:
    v = np.zeros(2 ** len(bits), dtype=complex)
    v[int(bits, 2)] = 1
    return v


def random_state(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=2**n) + 1j * rng.normal(size=2**n)
    return v / np.linalg.norm(v)


def ry(t):
    return np.array([[np.cos(t / 2), -np.sin(t / 2)], [np.sin(t / 2), np.cos(t / 2)]], dtype=complex)


# ---------- Bell ----------

def test_bell_states(ent):
    s = 1 / np.sqrt(2)
    np.testing.assert_allclose(ent.bell_state("phi+"), [s, 0, 0, s])
    np.testing.assert_allclose(ent.bell_state("phi-"), [s, 0, 0, -s])
    np.testing.assert_allclose(ent.bell_state("psi+"), [0, s, s, 0])
    np.testing.assert_allclose(ent.bell_state("psi-"), [0, s, -s, 0])
    assert np.iscomplexobj(ent.bell_state("phi+"))
    with pytest.raises(ValueError):
        ent.bell_state("ghz")


# ---------- Schmidt và entropy ----------

def test_product_state_has_one_schmidt_coefficient(ent):
    a = ry(0.7) @ basis("0")
    b = np.kron(ry(-1.3) @ basis("0"), ry(2.1) @ basis("0"))
    psi = np.kron(a, b)
    for n_a in (1, 2):
        lam = ent.schmidt_coefficients(psi, n_a)
        np.testing.assert_allclose(lam, [1.0], atol=1e-10)
        assert ent.entanglement_entropy(psi, n_a) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("kind", ["phi+", "phi-", "psi+", "psi-"])
def test_bell_is_maximally_entangled(ent, kind):
    psi = ent.bell_state(kind)
    np.testing.assert_allclose(ent.schmidt_coefficients(psi, 1), [2**-0.5, 2**-0.5])
    assert ent.entanglement_entropy(psi, 1) == pytest.approx(1.0)
    assert isinstance(ent.entanglement_entropy(psi, 1), float)


def test_partially_entangled_entropy(ent):
    # cos(t)|00> + sin(t)|11>: λ = (cos t, sin t), entropy là entropy nhị phân của cos² t
    t = 0.4
    psi = np.cos(t) * basis("00") + np.sin(t) * basis("11")
    p = np.cos(t) ** 2
    lam = ent.schmidt_coefficients(psi, 1)
    np.testing.assert_allclose(lam, [np.cos(t), np.sin(t)])
    assert lam[0] >= lam[1], "giảm dần"
    expected = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
    assert ent.entanglement_entropy(psi, 1) == pytest.approx(expected)


def test_cut_position_matters(ent):
    # |Φ+> trên wire (0, 1) và |0> ở wire 2: cắt sau wire 0 thì vướng 1 bit, cắt sau wire 1 thì 0
    psi = np.kron(ent.bell_state("phi+"), basis("0"))
    assert ent.entanglement_entropy(psi, 1) == pytest.approx(1.0)
    assert ent.entanglement_entropy(psi, 2) == pytest.approx(0.0, abs=1e-9)
    # wire 0 tách riêng, wire (1, 2) vướng: cắt sau wire 0 cho 0
    phi = np.kron(basis("1"), ent.bell_state("psi-"))
    assert ent.entanglement_entropy(phi, 1) == pytest.approx(0.0, abs=1e-9)
    assert ent.entanglement_entropy(phi, 2) == pytest.approx(1.0)


def test_schmidt_squares_sum_to_one_and_symmetric(ent):
    psi = random_state(5, 0)
    for n_a in (1, 2, 3, 4):
        lam = ent.schmidt_coefficients(psi, n_a)
        assert len(lam) <= 2 ** min(n_a, 5 - n_a)
        assert np.sum(lam**2) == pytest.approx(1.0)
    # entropy hai phía bằng nhau: S(A) = S(B)
    rev = psi.reshape((2,) * 5).transpose(4, 3, 2, 1, 0).reshape(-1)
    assert ent.entanglement_entropy(psi, 2) == pytest.approx(ent.entanglement_entropy(rev, 3))


# ---------- Phân phối biên ----------

def test_marginal_probabilities(ent):
    probs = np.abs(random_state(3, 1)) ** 2
    t = probs.reshape(2, 2, 2)
    np.testing.assert_allclose(ent.marginal_probabilities(probs, [0]), t.sum(axis=(1, 2)))
    np.testing.assert_allclose(ent.marginal_probabilities(probs, [2]), t.sum(axis=(0, 1)))
    np.testing.assert_allclose(ent.marginal_probabilities(probs, [0, 2]), t.sum(axis=1).reshape(-1))
    # thứ tự wire trong danh sách quyết định bit nào bên trái
    np.testing.assert_allclose(ent.marginal_probabilities(probs, [2, 0]), t.sum(axis=1).T.reshape(-1))


def test_bell_marginals_are_uniform_but_correlated(ent):
    probs = np.abs(ent.bell_state("phi+")) ** 2
    np.testing.assert_allclose(ent.marginal_probabilities(probs, [0]), [0.5, 0.5])
    np.testing.assert_allclose(ent.marginal_probabilities(probs, [1]), [0.5, 0.5])
    np.testing.assert_allclose(ent.marginal_probabilities(probs, [0, 1]), [0.5, 0, 0, 0.5])


# ---------- Ước lượng từ shots ----------

def test_expval_from_counts(ent):
    counts = {"00": 40, "11": 50, "01": 6, "10": 4}
    assert ent.expval_from_counts(counts, [0, 1]) == pytest.approx((40 + 50 - 6 - 4) / 100)
    assert ent.expval_from_counts(counts, [0]) == pytest.approx((40 + 6 - 50 - 4) / 100)
    assert ent.expval_from_counts(counts, [1]) == pytest.approx((40 + 4 - 50 - 6) / 100)
    assert isinstance(ent.expval_from_counts(counts, [0]), float)
    # ba wire, wire 0 là ký tự trái
    assert ent.expval_from_counts({"100": 3, "000": 1}, [0]) == pytest.approx(-0.5)
    assert ent.expval_from_counts({"100": 3, "000": 1}, [2]) == pytest.approx(1.0)


def test_expval_from_counts_unbiased_on_samples(ent):
    # cos(t)|00> + sin(t)|11>: <Z0 Z1> = 1, <Z0> = cos 2t
    t = 0.6
    psi = np.cos(t) * basis("00") + np.sin(t) * basis("11")
    rng = np.random.default_rng(0)
    out = rng.choice(4, size=20_000, p=np.abs(psi) ** 2)
    vals, cnt = np.unique(out, return_counts=True)
    counts = {format(v, "02b"): int(c) for v, c in zip(vals, cnt)}
    assert ent.expval_from_counts(counts, [0, 1]) == pytest.approx(1.0)
    est = ent.expval_from_counts(counts, [0])
    std = np.sqrt((1 - np.cos(2 * t) ** 2) / 20_000)
    assert abs(est - np.cos(2 * t)) < 5 * std


def test_shots_for_std(ent):
    assert ent.shots_for_std(0.01) == 10_000
    assert ent.shots_for_std(0.05) == 400
    assert ent.shots_for_std(0.1, expval=0.5) == 75       # (1 − 0.25) / 0.01
    assert ent.shots_for_std(0.1, expval=0.9) == 19       # (1 − 0.81) / 0.01 = 19
    assert ent.shots_for_std(0.001) == 1_000_000
    assert ent.shots_for_std(0.002, expval=0.3) == 227_500  # 0.91 / 0.002**2 = 227500.00000000003 trong float
    assert isinstance(ent.shots_for_std(0.05), int)
    # muốn std nhỏ đi 10 lần thì cần 100 lần shots
    assert ent.shots_for_std(0.002) == 100 * ent.shots_for_std(0.02)
