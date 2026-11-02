import math

import pytest
import torch
import torch.nn.functional as F

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("vae.ipynb")


def binary_data(n: int, seed: int) -> torch.Tensor:
    """n ảnh 784 pixel nhị phân sinh từ 4 mẫu gốc lật ngẫu nhiên 5% pixel."""
    g = torch.Generator().manual_seed(seed)
    protos = (torch.rand(4, 784, generator=g) < 0.3).float()
    x = protos[torch.randint(0, 4, (n,), generator=g)]
    flip = torch.rand(n, 784, generator=g) < 0.05
    return torch.where(flip, 1 - x, x)


def test_autoencoder_shapes(nb):
    torch.manual_seed(0)
    ae = nb.Autoencoder(8, hidden=32)
    x = torch.rand(5, 784)
    assert ae.encoder(x).shape == (5, 8)
    assert ae(x).shape == (5, 784)
    assert ae.decoder(torch.zeros(2, 8)).shape == (2, 784)


def test_vae_param_count_and_heads(nb):
    vae = nb.VAE(16)
    n = sum(p.numel() for p in vae.parameters())
    assert n == (784 * 512 + 512) + 2 * (512 * 16 + 16) + (16 * 512 + 512) + (512 * 784 + 784)
    mu, logvar = vae.encode(torch.rand(3, 784))
    assert mu.shape == logvar.shape == (3, 16)
    assert vae.decode(torch.zeros(3, 16)).shape == (3, 784)


def test_vae_forward_reparameterizes(nb):
    torch.manual_seed(1)
    vae = nb.VAE(4, hidden=32)
    x = torch.rand(6, 784)
    logits, mu, logvar = vae(x, torch.Generator().manual_seed(5))
    eps = torch.randn(mu.shape, generator=torch.Generator().manual_seed(5))
    torch.testing.assert_close(logits, vae.decode(mu + (0.5 * logvar).exp() * eps),
                               msg="z = mu + exp(logvar / 2) * eps, eps lấy từ generator")
    logits.sum().backward()
    assert vae.fc_logvar.weight.grad is not None and vae.fc_logvar.weight.grad.abs().sum() > 0


def test_vae_loss_terms(nb):
    torch.manual_seed(2)
    vae = nb.VAE(3, hidden=16)
    x = binary_data(7, 0)
    loss, recon, kl = nb.vae_loss(vae, x, 1.0, torch.Generator().manual_seed(3))
    logits, mu, logvar = vae(x, torch.Generator().manual_seed(3))
    exp_recon = F.binary_cross_entropy_with_logits(logits, x, reduction="none").sum(1).mean()
    exp_kl = (0.5 * (mu ** 2 + logvar.exp() - 1 - logvar).sum(1)).mean()
    torch.testing.assert_close(recon, exp_recon, msg="recon: cộng trên 784 pixel, trung bình theo batch")
    torch.testing.assert_close(kl, exp_kl)
    torch.testing.assert_close(loss, exp_recon + exp_kl)
    loss4, recon4, kl4 = nb.vae_loss(vae, x, 4.0, torch.Generator().manual_seed(3))
    torch.testing.assert_close(loss4, recon4 + 4.0 * kl4)
    assert loss.dim() == 0 and kl.item() > 0


def test_ae_loss(nb):
    torch.manual_seed(3)
    ae = nb.Autoencoder(4, hidden=16)
    x = binary_data(5, 1)
    torch.testing.assert_close(nb.ae_loss(ae, x), F.binary_cross_entropy_with_logits(ae(x), x, reduction="none").sum(1).mean())


def test_train_learns_and_is_reproducible(nb):
    X = binary_data(512, 2)
    runs = []
    for _ in range(2):
        torch.manual_seed(0)
        vae = nb.VAE(2, hidden=64)
        hist = nb.train(vae, lambda m, x, g: nb.vae_loss(m, x, 1.0, g)[0], X, epochs=3, lr=3e-3, batch_size=64, seed=4)
        runs.append(hist)
    assert len(runs[0]) == 3 and all(isinstance(v, float) for v in runs[0])
    assert runs[0] == runs[1], "cùng seed, cùng khởi tạo phải cho cùng history"
    assert runs[0][-1] < 0.7 * runs[0][0]
    assert not vae.training, "train xong để model ở eval()"


def test_train_history_is_per_sample_mean(nb):
    """lr = 0, loss = mean x[:, 0] của batch: history phải là mean trên mọi mẫu (batch cuối nhỏ hơn được tính đúng trọng số)."""
    X = torch.zeros(10, 784)
    X[:9, 0] = 1.0
    ae = nb.Autoencoder(2, hidden=4)
    loss_fn = lambda m, x, g: x[:, 0].mean() + 0 * sum(p.sum() for p in m.parameters())
    hist = nb.train(ae, loss_fn, X, epochs=2, lr=0.0, batch_size=4, seed=0)
    assert hist == pytest.approx([0.9, 0.9])


def quadrature_vae(nb, seed=0):
    """VAE latent 1 chiều; q(z|x) cố định N(0, 4) (encoder bằng 0), decoder ngẫu nhiên độ dốc nhỏ: log p(x) tính được bằng tích phân số."""
    torch.manual_seed(seed)
    vae = nb.VAE(1, hidden=8).double()
    with torch.no_grad():
        for p in list(vae.encoder.parameters()) + list(vae.fc_mu.parameters()) + [vae.fc_logvar.weight]:
            p.zero_()
        vae.fc_logvar.bias.fill_(math.log(4.0))
        g = torch.Generator().manual_seed(seed + 1)
        vae.decoder[0].weight.copy_(torch.randn(8, 1, generator=g, dtype=torch.float64))
        vae.decoder[0].bias.copy_(torch.randn(8, generator=g, dtype=torch.float64))
        vae.decoder[2].weight.copy_(0.05 * torch.randn(784, 8, generator=g, dtype=torch.float64))
        vae.decoder[2].bias.copy_(torch.randn(784, generator=g, dtype=torch.float64))
    return vae


def exact_log_px(vae, X):
    z = torch.linspace(-9, 9, 6001, dtype=torch.float64)[:, None]
    dz = (z[1] - z[0]).item()
    with torch.no_grad():
        logits = vae.decode(z)
        log_pz = -0.5 * (z[:, 0] ** 2 + math.log(2 * math.pi))
        out = []
        for x in X:
            log_px_z = -F.binary_cross_entropy_with_logits(logits, x.expand_as(logits), reduction="none").sum(1)
            out.append(torch.logsumexp(log_px_z + log_pz, 0) + math.log(dz))
    return torch.stack(out)


def test_iwae_matches_numerical_integral(nb):
    vae = quadrature_vae(nb)
    X = binary_data(4, 3).double()
    exact = -exact_log_px(vae, X).mean().item()
    est = nb.iwae_nll(vae, X, K=4000, batch_size=2, seed=0)
    assert isinstance(est, float)
    assert est == pytest.approx(exact, abs=0.05), "-L_K với K lớn phải tiến tới -log p(x) tính bằng tích phân số"
    assert nb.iwae_nll(vae, X, K=4000, batch_size=2, seed=0) == est, "cùng seed cho cùng kết quả"


def test_iwae_bound_ordering(nb):
    vae = quadrature_vae(nb, seed=1)
    with torch.no_grad():
        vae.fc_mu.bias.fill_(1.5)
        vae.fc_logvar.bias.fill_(math.log(0.5))
    X = binary_data(4, 4).double()
    exact = -exact_log_px(vae, X).mean().item()
    k1 = sum(nb.iwae_nll(vae, X, K=1, seed=s) for s in range(200)) / 200
    k50 = sum(nb.iwae_nll(vae, X, K=50, seed=s) for s in range(20)) / 20
    assert k1 - exact > 0.5, "q lệch khỏi posterior: -ELBO cách -log p(x) rõ rệt"
    assert k1 > k50 > exact - 0.02, "-ELBO (K = 1) > -L_50 > -log p(x)"
    assert k50 - exact < 0.5 * (k1 - exact)


def test_active_units(nb):
    torch.manual_seed(5)
    vae = nb.VAE(6, hidden=32)
    with torch.no_grad():
        vae.fc_mu.weight[:2] = 0.0
        vae.fc_mu.weight[2:] *= 20
        vae.fc_logvar.weight.mul_(50)
    X = binary_data(300, 5)
    assert nb.active_units(vae, X) == 4, "chiều có mean encoder không đổi theo ảnh là chiều chết, kể cả khi logvar thay đổi"
    assert nb.active_units(vae, X, threshold=1e9) == 0
