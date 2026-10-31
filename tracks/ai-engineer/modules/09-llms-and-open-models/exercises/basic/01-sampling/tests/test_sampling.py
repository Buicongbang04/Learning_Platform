import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Phân phối 4 token dùng xuyên suốt: logits = ln(p) nên softmax(logits) = p.
P = np.array([0.5, 0.3, 0.15, 0.05])
LOGITS = np.log(P)


@pytest.fixture(scope="module")
def s():
    return ex.module("sampling.py")


def frequencies(s, n=20_000, seed=0, **kwargs):
    rng = np.random.default_rng(seed)
    counts = np.zeros(4)
    for _ in range(n):
        counts[s.sample_next(LOGITS, rng, **kwargs)] += 1
    return counts / n


# ---------- softmax, greedy ----------


def test_softmax_matches_definition(s):
    z = np.array([1.0, 2.0, 0.5])
    np.testing.assert_allclose(s.softmax(z), np.exp(z) / np.exp(z).sum(), rtol=1e-12)
    np.testing.assert_allclose(s.softmax(LOGITS), P, rtol=1e-12)


def test_softmax_temperature(s):
    np.testing.assert_allclose(s.softmax(LOGITS, temperature=2.0), np.sqrt(P) / np.sqrt(P).sum(), rtol=1e-12)
    sharp = s.softmax(LOGITS, temperature=0.25)
    np.testing.assert_allclose(sharp, P**4 / (P**4).sum(), rtol=1e-12)
    assert sharp[0] > 0.85, "temperature nhỏ làm phân phối nhọn hơn"
    with pytest.raises(ValueError):
        s.softmax(LOGITS, temperature=0.0)


def test_softmax_stable_and_handles_minus_inf(s):
    out = s.softmax(np.array([1000.0, 999.0, -np.inf]))
    assert np.all(np.isfinite(out)), "logit lớn không được làm exp tràn: trừ max trước"
    np.testing.assert_allclose(out, [1 / (1 + np.exp(-1)), np.exp(-1) / (1 + np.exp(-1)), 0.0], rtol=1e-12)
    assert out.sum() == pytest.approx(1.0)


def test_greedy(s):
    assert s.greedy(LOGITS) == 0
    assert s.greedy(np.array([0.1, 3.0, 3.0, -1.0])) == 1, "bằng nhau thì chỉ số nhỏ nhất"
    assert type(s.greedy(LOGITS)) is int


# ---------- top-k, top-p ----------


def test_top_k_keeps_k_largest(s):
    z = np.array([0.1, 2.0, -1.0, 1.5, 0.7])
    out = s.top_k_filter(z, 2)
    assert np.isinf(out[[0, 2, 4]]).all() and (out[[0, 2, 4]] < 0).all()
    np.testing.assert_array_equal(out[[1, 3]], [2.0, 1.5])
    np.testing.assert_array_equal(z, [0.1, 2.0, -1.0, 1.5, 0.7], err_msg="không sửa mảng đầu vào")


def test_top_k_ties_and_bounds(s):
    z = np.array([1.0, 3.0, 2.0, 2.0, 0.0])
    assert np.isfinite(s.top_k_filter(z, 2)).sum() == 3, "bằng logit thứ k ở biên thì giữ hết"
    np.testing.assert_array_equal(s.top_k_filter(z, 0), z)
    np.testing.assert_array_equal(s.top_k_filter(z, 5), z)
    np.testing.assert_array_equal(s.top_k_filter(z, 9), z)


@pytest.mark.parametrize("p, kept", [(0.4, [0]), (0.75, [0, 1]), (0.85, [0, 1, 2]), (0.97, [0, 1, 2, 3])])
def test_top_p_smallest_set_reaching_p(s, p, kept):
    out = s.top_p_filter(LOGITS, p)
    assert list(np.flatnonzero(np.isfinite(out))) == kept, (
        "giữ tập nhỏ nhất có tổng >= p, kể cả token làm tổng vượt p"
    )
    np.testing.assert_array_equal(out[kept], LOGITS[kept])


def test_top_p_unsorted_and_bounds(s):
    z = np.log(np.array([0.05, 0.3, 0.15, 0.5]))
    assert list(np.flatnonzero(np.isfinite(s.top_p_filter(z, 0.75)))) == [1, 3], "sắp theo xác suất, không theo vị trí"
    assert np.isfinite(s.top_p_filter(z, 1e-9)).sum() == 1, "luôn giữ ít nhất 1 token"
    np.testing.assert_array_equal(s.top_p_filter(z, 1.0), z)
    np.testing.assert_array_equal(z, np.log(np.array([0.05, 0.3, 0.15, 0.5])))


def test_top_p_ties_prefer_lower_index(s):
    z = np.zeros(4)                       # 4 token cùng xác suất 0.25
    assert list(np.flatnonzero(np.isfinite(s.top_p_filter(z, 0.5)))) == [0, 1]


# ---------- penalties ----------


def test_repetition_penalty_sign_aware(s):
    z = np.array([2.0, -1.0, 0.5, 3.0])
    out = s.apply_repetition_penalty(z, [0, 1, 1, 1], 2.0)
    np.testing.assert_allclose(
        out, [1.0, -2.0, 0.5, 3.0],
        err_msg="logit dương chia cho penalty, logit âm nhân với penalty, token lặp chỉ phạt một lần",
    )
    np.testing.assert_array_equal(z, [2.0, -1.0, 0.5, 3.0])
    np.testing.assert_array_equal(s.apply_repetition_penalty(z, [0, 3], 1.0), z)
    np.testing.assert_array_equal(s.apply_repetition_penalty(z, [], 1.5), z)


def test_presence_frequency(s):
    z = np.zeros(5)
    out = s.apply_presence_frequency(z, [1, 1, 1, 3], presence=0.5, frequency=0.2)
    np.testing.assert_allclose(out, [0.0, -1.1, 0.0, -0.7, 0.0])
    np.testing.assert_array_equal(z, np.zeros(5))
    np.testing.assert_array_equal(s.apply_presence_frequency(z, []), z)


# ---------- sample_next ----------


def test_temperature_zero_is_greedy_without_rng(s):
    rng = np.random.default_rng(1)
    state = rng.bit_generator.state
    assert s.sample_next(LOGITS, rng, temperature=0) == 0
    assert rng.bit_generator.state == state, "temperature 0 là greedy, không rút ngẫu nhiên"
    z = np.array([2.0, 1.9, -5.0])
    assert s.sample_next(z, rng, temperature=0, repetition_penalty=1.2, generated=[0]) == 1, (
        "repetition penalty áp trước khi chọn greedy"
    )


def test_samples_follow_distribution(s):
    f = frequencies(s)
    np.testing.assert_allclose(f, P, atol=0.015)
    assert type(s.sample_next(LOGITS, np.random.default_rng(0))) is int


def test_sample_reproducible_with_seed(s):
    a = [s.sample_next(LOGITS, np.random.default_rng(7), temperature=0.8) for _ in range(3)]
    rng1, rng2 = np.random.default_rng(3), np.random.default_rng(3)
    seq1 = [s.sample_next(LOGITS, rng1) for _ in range(50)]
    seq2 = [s.sample_next(LOGITS, rng2) for _ in range(50)]
    assert seq1 == seq2 and len(set(a)) == 1


def test_sample_top_k_top_p_support(s):
    f = frequencies(s, top_k=2)
    assert f[2] == 0 and f[3] == 0
    np.testing.assert_allclose(f[:2], [0.625, 0.375], atol=0.015)
    f = frequencies(s, top_p=0.75)
    assert f[2] == 0 and f[3] == 0
    np.testing.assert_allclose(f[:2], [0.625, 0.375], atol=0.015)


def test_temperature_applied_before_top_p(s):
    # T = 2: xác suất ~ sqrt(P) = [0.379, 0.293, 0.207, 0.120]; top_p 0.75 phải giữ 3 token.
    f = frequencies(s, temperature=2.0, top_p=0.75)
    q = np.sqrt(P)[:3] / np.sqrt(P)[:3].sum()
    assert f[3] == 0
    np.testing.assert_allclose(f[:3], q, atol=0.015)


def test_sample_repetition_penalty_changes_distribution(s):
    # phạt token 0 (logit ln 0.5 < 0 nên bị nhân 2): logit thành 2 ln 0.5 = ln 0.25
    f = frequencies(s, repetition_penalty=2.0, generated=[0, 0])
    q = np.array([0.25, 0.3, 0.15, 0.05]) / 0.75
    np.testing.assert_allclose(f, q, atol=0.015)


def test_sample_does_not_mutate_logits(s):
    z = LOGITS.copy()
    s.sample_next(z, np.random.default_rng(0), temperature=0.7, top_k=3, top_p=0.9, repetition_penalty=1.3,
                  generated=[0, 1])
    np.testing.assert_array_equal(z, LOGITS)
