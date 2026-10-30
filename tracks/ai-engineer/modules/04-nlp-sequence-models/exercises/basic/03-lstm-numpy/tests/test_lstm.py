import numpy as np
import pytest
import torch
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def L():
    return ex.module("lstm.py")


def torch_lstm(layer) -> torch.nn.LSTM:
    D, H = layer.W_ih.shape[1], layer.W_hh.shape[1]
    ref = torch.nn.LSTM(D, H).double()
    with torch.no_grad():
        ref.weight_ih_l0.copy_(torch.tensor(layer.W_ih))
        ref.weight_hh_l0.copy_(torch.tensor(layer.W_hh))
        ref.bias_ih_l0.copy_(torch.tensor(layer.b_ih))
        ref.bias_hh_l0.copy_(torch.tensor(layer.b_hh))
    return ref


def test_init_shapes_and_range(L):
    layer = L.LSTM(3, 50, np.random.default_rng(0))
    assert layer.W_ih.shape == (200, 3) and layer.W_hh.shape == (200, 50)
    assert layer.b_ih.shape == (200,) and layer.b_hh.shape == (200,)
    k = 1 / np.sqrt(50)
    for p in (layer.W_ih, layer.W_hh, layer.b_ih, layer.b_hh):
        assert p.dtype == np.float64 and np.all(np.abs(p) <= k)
    assert layer.W_hh.std() == pytest.approx(k / np.sqrt(3), rel=0.05), "phân phối đều U(-k, k)"
    assert layer.b_ih.std() == pytest.approx(k / np.sqrt(3), rel=0.2), "bias cũng khởi tạo U(-k, k) như nn.LSTM"
    again = L.LSTM(3, 50, np.random.default_rng(0))
    assert np.array_equal(layer.W_hh, again.W_hh) and np.array_equal(layer.b_hh, again.b_hh)


def test_forward_matches_torch(L):
    rng = np.random.default_rng(1)
    layer = L.LSTM(4, 6, rng)
    x = rng.normal(size=(7, 3, 4))
    h0, c0 = rng.normal(size=(3, 6)), rng.normal(size=(3, 6))
    out, (hT, cT) = layer.forward(x, h0, c0)
    ref_out, (ref_h, ref_c) = torch_lstm(layer)(torch.tensor(x), (torch.tensor(h0)[None], torch.tensor(c0)[None]))
    assert out.shape == (7, 3, 6)
    np.testing.assert_allclose(out, ref_out.detach().numpy(), atol=1e-12,
                               err_msg="thứ tự cổng phải là i, f, g, o như nn.LSTM")
    np.testing.assert_allclose(hT, ref_h[0].detach().numpy(), atol=1e-12)
    np.testing.assert_allclose(cT, ref_c[0].detach().numpy(), atol=1e-12)


def test_forward_default_zero_state(L):
    rng = np.random.default_rng(2)
    layer = L.LSTM(2, 3, rng)
    x = rng.normal(size=(4, 5, 2))
    a, _ = layer.forward(x)
    b, _ = layer.forward(x, np.zeros((5, 3)), np.zeros((5, 3)))
    np.testing.assert_allclose(a, b)


def test_forward_stable_for_large_inputs(L):
    layer = L.LSTM(2, 3, np.random.default_rng(3))
    x = np.full((3, 2, 2), 1e4)
    x[:, 1] = -1e4
    with np.errstate(over="raise", invalid="raise"):
        out, (h, c) = layer.forward(x)
    assert np.all(np.isfinite(out)) and np.all(np.abs(out) <= 1)


def test_backward_matches_torch(L):
    rng = np.random.default_rng(4)
    layer = L.LSTM(3, 5, rng)
    x = rng.normal(size=(6, 2, 3))
    h0, c0 = rng.normal(size=(2, 5)), rng.normal(size=(2, 5))
    G = rng.normal(size=(6, 2, 5))                  # loss = sum(out * G) + sum(h_T * Gh) + sum(c_T * Gc)
    Gh, Gc = rng.normal(size=(2, 5)), rng.normal(size=(2, 5))

    layer.forward(x, h0, c0)
    dx = layer.backward(G, Gh, Gc)

    ref = torch_lstm(layer)
    tx = torch.tensor(x, requires_grad=True)
    th0 = torch.tensor(h0[None], requires_grad=True)
    tc0 = torch.tensor(c0[None], requires_grad=True)
    out, (hT, cT) = ref(tx, (th0, tc0))
    ((out * torch.tensor(G)).sum() + (hT[0] * torch.tensor(Gh)).sum() + (cT[0] * torch.tensor(Gc)).sum()).backward()

    np.testing.assert_allclose(dx, tx.grad.numpy(), atol=1e-10)
    np.testing.assert_allclose(layer.dW_ih, ref.weight_ih_l0.grad.numpy(), atol=1e-10)
    np.testing.assert_allclose(layer.dW_hh, ref.weight_hh_l0.grad.numpy(), atol=1e-10,
                               err_msg="dW_hh cộng dồn qua mọi bước thời gian")
    np.testing.assert_allclose(layer.db_ih, ref.bias_ih_l0.grad.numpy(), atol=1e-10)
    np.testing.assert_allclose(layer.db_hh, ref.bias_hh_l0.grad.numpy(), atol=1e-10)
    np.testing.assert_allclose(layer.dh0, th0.grad[0].numpy(), atol=1e-10)
    np.testing.assert_allclose(layer.dc0, tc0.grad[0].numpy(), atol=1e-10,
                               err_msg="gradient chảy về c_{t-1} qua dc * f")


def test_backward_default_and_overwrite(L):
    rng = np.random.default_rng(5)
    layer = L.LSTM(2, 3, rng)
    x = rng.normal(size=(4, 2, 2))
    G = rng.normal(size=(4, 2, 3))
    layer.forward(x)
    dx1 = layer.backward(G)
    dW1 = layer.dW_hh.copy()
    layer.forward(x)
    dx2 = layer.backward(G, np.zeros((2, 3)), np.zeros((2, 3)))
    np.testing.assert_allclose(dx1, dx2)
    np.testing.assert_allclose(layer.dW_hh, dW1, err_msg="gán gradient mới, không cộng dồn qua các lần gọi")


def test_clip_grad_norm_matches_torch(L):
    rng = np.random.default_rng(6)
    grads = [rng.normal(size=(4, 3)), rng.normal(size=5)]
    params = [torch.zeros(g.shape, dtype=torch.float64, requires_grad=True) for g in grads]
    for p, g in zip(params, grads):
        p.grad = torch.tensor(g.copy())
    ref_total = torch.nn.utils.clip_grad_norm_(params, 1.0).item()
    arrays = [g.copy() for g in grads]
    total = L.clip_grad_norm(arrays, 1.0)
    assert total == pytest.approx(ref_total)
    for a, p in zip(arrays, params):
        np.testing.assert_allclose(a, p.grad.numpy(), atol=1e-12)
    small = [np.array([0.3, 0.4])]
    assert L.clip_grad_norm(small, 1.0) == pytest.approx(0.5)
    np.testing.assert_allclose(small[0], [0.3, 0.4], err_msg="chuẩn dưới ngưỡng thì không đổi")


def test_lstm_keeps_gradient_over_long_sequences(L):
    # Bias cổng quên = 3 (σ ≈ 0.95): gradient từ bước cuối về bước đầu sau 50 bước vẫn đáng kể.
    rng = np.random.default_rng(7)
    layer = L.LSTM(1, 8, rng)
    layer.b_ih[8:16] = 3.0
    layer.b_hh[8:16] = 0.0
    x = rng.normal(size=(50, 1, 1))
    layer.forward(x)
    G = np.zeros((50, 1, 8))
    G[-1] = 1.0
    dx = layer.backward(G)
    assert np.abs(dx[0]).max() > 1e-4 * np.abs(dx[-1]).max()
