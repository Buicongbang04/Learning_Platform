---
title: Autoencoder và VAE trên MNIST, đo ELBO, cận IWAE và posterior collapse
level: intermediate
services: []
files:
  - path: starter/vae.ipynb
    note: 2 lớp, 5 hàm TODO
  - path: tests/test_vae_mnist.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py mnist
  - uv run jupyter lab tracks/ai-engineer/modules/06-generative-models/exercises/intermediate/01-vae-mnist/starter/vae.ipynb
  - uv run pytest tracks/ai-engineer/modules/06-generative-models/exercises/intermediate/01-vae-mnist -q
---

## Mục tiêu

Dựng một autoencoder và một VAE cùng kiến trúc MLP, train trên MNIST, rồi đo cho ra số ba điều lý thuyết nói bằng lời: VAE đổi bao
nhiêu chất lượng tái tạo để lấy khả năng sinh, ELBO cách log-likelihood thật bao xa (cận IWAE), và $$\beta$$ lớn giết bao nhiêu chiều latent.
Làm xong bạn tự tin đọc và báo cáo con số của một model biến ẩn: nats/ảnh, bits/dim, KL, active units.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Cả notebook chạy khoảng 5 phút trên CPU 4 luồng (6 model MLP, mỗi model 20 epoch trên 60 000 ảnh, khoảng 45
giây); kernel `ai-gpu` thì tự dùng GPU. Test chạy trên CPU với dữ liệu sinh trong test, vài giây.

Đọc mục 2, 3 phần lý thuyết. Mở `starter/vae.ipynb`:

1. `Autoencoder(latent_dim, hidden=512)` và `VAE(latent_dim, hidden=512)` đúng cấu trúc trong notebook (MLP, decoder trả logits; VAE có
   `encode`, `decode`, `forward(x, generator)` lấy một mẫu bằng reparameterization).
2. `ae_loss`, `vae_loss(model, x, beta, generator)` trả `(loss, recon, kl)` theo nats mỗi ảnh, và `train(model, loss_fn, X, epochs, ...)`
   tái lập theo `seed`, trả loss trung bình theo mẫu mỗi epoch.
3. `iwae_nll(model, X, K, ...)`: ước lượng $$-\log p(x)$$ bằng cận $$\mathcal{L}_K$$; `active_units(model, X, threshold)`.

Rồi chạy các cell `explore`: AE và VAE latent 16 cùng ngân sách, đo trên test (tái tạo, KL, $$-\mathcal{L}_1$$, $$-\mathcal{L}_{100}$$, active units), sinh ảnh
từ $$z \sim \mathcal{N}(0, I)$$ cho cả hai và chấm bằng một classifier, quét $$\beta \in \{0.5, 1, 4, 10\}$$, vẽ latent 2 chiều và nội suy. Sau đó làm
phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `Autoencoder`, `VAE` đúng shape và số tham số; `forward` của VAE dùng $$z = \mu + e^{\text{logvar}/2}\varepsilon$$ với $$\varepsilon$$ từ `generator`, gradient
  về được `fc_logvar`.
- `vae_loss`: tái tạo cộng trên 784 pixel rồi trung bình theo batch, KL dạng đóng, `loss = recon + beta * kl`; `ae_loss` đúng BCE theo ảnh.
- `train` học được dữ liệu nhị phân sinh trong test (loss giảm hơn 30% sau 3 epoch), cùng seed cho cùng history, loss theo mẫu (batch
  cuối nhỏ hơn được tính đúng trọng số), xong ở `eval()`.
- `iwae_nll` với $$K = 4000$$ khớp $$-\log p(x)$$ tính bằng tích phân số trên VAE latent 1 chiều (sai số dưới 0.05 nats), và
  $$-\mathcal{L}_1 > -\mathcal{L}_{50} > -\log p(x)$$ khi $$q$$ lệch posterior.
- `active_units` đếm đúng chiều có $$\mathrm{Var}_x(\mu_j) >$$ ngưỡng, không bị đánh lừa bởi `logvar` thay đổi.

## Gợi ý

### Gợi ý 1

Viết `vae_loss` từ ba mảnh của bài Basic 01 (KL dạng đóng, reparameterization, Bernoulli bằng logits); thang đo là chỗ dễ sai nhất:
`binary_cross_entropy_with_logits` mặc định lấy trung bình trên **mọi phần tử**. Trong `train`, loss trung bình theo mẫu là tổng
`loss × số mẫu của batch` chia tổng số mẫu.

### Gợi ý 2

Với `iwae_nll`, lấy $$K$$ mẫu cho cả batch một lần (tensor `(K, B, latent)`), decode chúng như một batch lớn, tính ba log-mật độ shape `(K, B)` rồi
log-sum-exp trên chiều $$K$$. $$\log q(z_k \mid x)$$ viết được qua chính $$\varepsilon$$ đã dùng: $$(z - \mu)/\sigma = \varepsilon$$.
