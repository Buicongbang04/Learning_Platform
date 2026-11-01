"""Các mảnh toán của VAE: KL dạng đóng, reparameterization, log-likelihood, ELBO và cận importance-weighted.

Quy ước: encoder trả `mu`, `logvar` (log phương sai, không phải log std) shape (B, D); mọi đại lượng "theo
mẫu" trả shape (B,), đã cộng trên mọi chiều; đơn vị nats (log cơ số e).
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F


def gaussian_kl(mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
    """KL( N(mu, diag(exp(logvar))) || N(0, I) ) theo từng mẫu, shape (B,)."""
    return 0.5 * (mu.pow(2) + logvar.exp() - 1 - logvar).sum(dim=1)


def reparameterize(mu: torch.Tensor, logvar: torch.Tensor, generator: torch.Generator | None = None) -> torch.Tensor:
    """z = mu + sigma * eps, eps ~ N(0, I) lấy từ `generator`; gradient phải chảy về mu và logvar."""
    eps = torch.randn(mu.shape, generator=generator, dtype=mu.dtype, device=mu.device)
    return mu + (0.5 * logvar).exp() * eps


def bernoulli_log_likelihood(logits: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """log p(x | z) với p = Bernoulli(sigmoid(logits)) từng pixel, x trong [0, 1]; cộng mọi chiều trừ chiều 0.

    Phải ổn định số khi |logits| rất lớn (không tính sigmoid rồi mới lấy log).
    """
    ll = x * logits - F.softplus(logits)
    return ll.flatten(1).sum(dim=1)


def gaussian_log_density(z: torch.Tensor, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
    """log N(z; mu, diag(exp(logvar))) cộng trên chiều cuối; các chiều đầu được broadcast."""
    return -0.5 * (math.log(2 * math.pi) + logvar + (z - mu).pow(2) / logvar.exp()).sum(dim=-1)


def elbo(logits: torch.Tensor, x: torch.Tensor, mu: torch.Tensor, logvar: torch.Tensor, beta: float = 1.0) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """(elbo, recon, kl), mỗi cái shape (B,). recon = log p(x | z) Bernoulli, elbo = recon - beta * kl.

    Loss để minimize là -elbo.mean().
    """
    recon = bernoulli_log_likelihood(logits, x)
    kl = gaussian_kl(mu, logvar)
    return recon - beta * kl, recon, kl


def importance_log_likelihood(log_px_given_z: torch.Tensor, log_pz: torch.Tensor, log_qz: torch.Tensor) -> torch.Tensor:
    """Ước lượng log p(x) bằng K mẫu z_k ~ q(z | x): log (1/K) sum_k p(x|z_k) p(z_k) / q(z_k|x).

    Ba input shape (K, B). Trả (B,). Phải ổn định số khi log-weight cỡ -1000.
    """
    log_w = log_px_given_z + log_pz - log_qz
    return torch.logsumexp(log_w, dim=0) - math.log(log_w.shape[0])
