---
title: ELBO của VAE tự viết, từ KL tới cận importance-weighted
level: basic
services: []
files:
  - path: starter/vae.py
    note: 6 hàm TODO
  - path: tests/test_vae.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/06-generative-models/exercises/basic/01-vae-elbo -q
---

## Mục tiêu

Viết các mảnh toán làm nên một VAE mà không cần mạng nơ-ron nào: KL dạng đóng giữa hai Gauss, reparameterization trick,
log-likelihood Bernoulli ổn định số, ELBO, và ước lượng log-likelihood bằng importance sampling. Test kiểm chúng trên một
model tuyến tính Gauss, nơi $$\log p(x)$$ tính được chính xác, nên bạn **thấy** ELBO là cận dưới và cận IWAE chặt dần khi tăng
số mẫu. Bài Intermediate 01 ghép chúng vào một VAE trên MNIST.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 3 phần lý thuyết. Trong `starter/vae.py`, encoder được giả định trả `mu` và `logvar` (log **phương sai**) shape
`(B, D)`; mọi đại lượng "theo mẫu" trả shape `(B,)`, đã cộng trên mọi chiều, đơn vị nats. Chỉ dùng torch.

1. `gaussian_kl(mu, logvar)`: $$\mathrm{KL}\big(\mathcal{N}(\mu, \mathrm{diag}(e^{\text{logvar}}))\,\|\,\mathcal{N}(0, I)\big)$$ theo từng mẫu.
2. `reparameterize(mu, logvar, generator=None)`: một mẫu $$z = \mu + \sigma\odot\varepsilon$$, $$\varepsilon$$ lấy bằng **một** lần
   `torch.randn(mu.shape, generator=generator, ...)` (cùng dtype, device với `mu`). Gradient phải chảy về cả `mu` và `logvar`.
3. `bernoulli_log_likelihood(logits, x)`: $$\log p(x \mid z)$$ với $$x_i \sim \mathrm{Bernoulli}(\sigma(\text{logit}_i))$$, $$x \in [0, 1]$$, input shape
   bất kỳ `(B, ...)`, cộng mọi chiều trừ chiều batch. Ổn định khi `|logits|` cỡ 100 (không tính `sigmoid` rồi mới `log`).
4. `gaussian_log_density(z, mu, logvar)`: $$\log\mathcal{N}(z;\ \mu, \mathrm{diag}(e^{\text{logvar}}))$$ cộng trên **chiều cuối**, các chiều đầu broadcast
   (vd. `z` shape `(K, B, D)` với `mu` shape `(B, D)` trả `(K, B)`).
5. `elbo(logits, x, mu, logvar, beta=1.0)`: trả `(elbo, recon, kl)` theo từng mẫu, `recon` là log-likelihood Bernoulli,
   $$\text{elbo} = \text{recon} - \beta\,\text{kl}$$.
6. `importance_log_likelihood(log_px_given_z, log_pz, log_qz)`: ba tensor shape `(K, B)` cho $$K$$ mẫu $$z_k \sim q(z \mid x)$$; trả
   $$\mathcal{L}_K = \log\frac1K\sum_k \frac{p(x \mid z_k)\,p(z_k)}{q(z_k \mid x)}$$ shape `(B,)`, ổn định khi các log-weight cỡ -1000.

## Tiêu chí đạt

- `gaussian_kl` khớp `torch.distributions.kl_divergence` (cộng trên chiều), bằng 0 tại $$\mu = 0$$, $$\log\sigma^2 = 0$$, dương ở chỗ khác.
- `reparameterize` tái lập theo `generator`, đúng công thức với $$\sigma = e^{\text{logvar}/2}$$; gradient theo `mu` là 1, theo `logvar` là
  $$\tfrac12\sigma\varepsilon$$; 200 000 mẫu có mean và phương sai đúng.
- `bernoulli_log_likelihood` khớp `binary_cross_entropy_with_logits` (dấu ngược, cộng theo mẫu) và hữu hạn, đúng ở logits ±100.
- `gaussian_log_density` khớp `torch.distributions.Normal` và broadcast đúng.
- `elbo` = recon − β·kl, đúng với β = 4.
- Trên model tuyến tính Gauss: khi $$q$$ là posterior thật, $$\mathcal{L}_K$$ bằng đúng $$\log p(x)$$; khi $$q$$ lệch, ELBO ($$K = 1$$) $$<$$ $$\mathcal{L}_{200}$$ $$\le \log p(x)$$
  và $$\mathcal{L}_{200}$$ đóng hơn nửa khoảng hở; log-weight cỡ -1000 cho kết quả hữu hạn, đúng.

## Gợi ý

### Gợi ý 1

Viết KL cho một chiều trước: $$\mathrm{KL}(\mathcal{N}(\mu, \sigma^2)\,\|\,\mathcal{N}(0, 1)) = \tfrac12(\mu^2 + \sigma^2 - 1 - \log\sigma^2)$$, rồi cộng trên các chiều vì
các chiều độc lập. Với Bernoulli, viết $$\log\sigma(l)$$ và $$\log(1 - \sigma(l))$$ qua hàm `softplus` (mục 2 module 01: luôn làm việc trong
không gian log).

### Gợi ý 2

Gradient theo `logvar` chỉ chảy được nếu $$\sigma$$ được **tính từ** `logvar` trong graph, còn $$\varepsilon$$ là hằng số. Với cận IWAE, trung bình
của các tỉ số nằm **trong** log: đó là một log-sum-exp trên chiều $$K$$ trừ $$\log K$$, không phải trung bình của các log-weight (cái đó là
ELBO).
