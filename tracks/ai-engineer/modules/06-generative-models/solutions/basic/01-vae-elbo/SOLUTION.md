# Lời giải: ELBO của VAE tự viết

## Cách làm

| Hàm | Công thức | Ghi chú cài đặt |
| --- | --- | --- |
| `gaussian_kl` | $$\tfrac12\sum_j(\mu_j^2 + e^{\text{logvar}_j} - 1 - \text{logvar}_j)$$ | `.sum(dim=1)`, không `.mean` |
| `reparameterize` | $$\mu + e^{\text{logvar}/2}\odot\varepsilon$$ | $$\varepsilon$$ từ `generator`; không `detach` |
| `bernoulli_log_likelihood` | $$\sum_i x_i l_i - \mathrm{softplus}(l_i)$$ | `flatten(1).sum(1)` |
| `gaussian_log_density` | $$-\tfrac12\sum(\log 2\pi + \text{logvar} + (z - \mu)^2 e^{-\text{logvar}})$$ | cộng trên `dim=-1` |
| `elbo` | recon − β·kl | trả cả ba để log riêng từng phần |
| `importance_log_likelihood` | $$\mathrm{logsumexp}_k(\log w_k) - \log K$$ | $$\log w = \log p(x \mid z) + \log p(z) - \log q(z \mid x)$$ |

**Bernoulli ổn định số.** $$\log\sigma(l) = -\mathrm{softplus}(-l)$$ và $$\log(1 - \sigma(l)) = -\mathrm{softplus}(l)$$, nên
$$x\log\sigma(l) + (1 - x)\log(1 - \sigma(l)) = x\,l - \mathrm{softplus}(l)$$. `F.softplus` của torch đã ổn định với đối số lớn (trả về chính
đối số khi vượt ngưỡng). Bản `torch.log(torch.sigmoid(l))` ra `-inf` khi $$l = -100$$ trong float32 (sigmoid underflow về 0), test với
logits ±100 bắt được.

**Reparameterization.** Gradient: $$\partial z/\partial\mu = 1$$, $$\partial z/\partial\,\text{logvar} = \tfrac12 e^{\text{logvar}/2}\varepsilon$$. Test so đúng hai
giá trị này. Ba cách sai hay gặp đều bị bắt: dùng $$e^{\text{logvar}}$$ làm std (sai thang đo), lấy $$\varepsilon$$ không qua `generator` (không tái
lập), và `.detach()` hay tạo $$z$$ trong `torch.no_grad()` (gradient không về encoder).

**Cận IWAE.** Mỗi log-weight cỡ hàng trăm nats âm; `exp` trực tiếp underflow về 0 rồi `log(0) = -inf`. Log-sum-exp trừ max trước
khi lấy mũ (mục 2 module 01). Trung bình phải nằm trong log: $$\log\frac1K\sum w_k \ge \frac1K\sum\log w_k$$ theo Jensen, vế phải là ước
lượng ELBO bằng $$K$$ mẫu, không chặt hơn khi tăng $$K$$.

## Vì sao test dùng model tuyến tính Gauss

Với $$z \sim \mathcal{N}(0, I)$$, $$x \mid z \sim \mathcal{N}(Wz + b, s^2 I)$$, cả $$p(x) = \mathcal{N}(b, WW^\top + s^2 I)$$ lẫn posterior
$$p(z \mid x) = \mathcal{N}\big(\Sigma W^\top(x - b)/s^2,\ \Sigma\big)$$, $$\Sigma = (I + W^\top W/s^2)^{-1}$$ đều có dạng đóng. Test dùng điều đó theo hai cách:

- Chọn $$W$$ có các cột trực giao để posterior là Gauss **đường chéo**; khi đó $$q$$ đúng bằng posterior, mọi trọng số $$p(x, z)/q(z \mid x)$$
  bằng đúng $$p(x)$$, và $$\mathcal{L}_K$$ phải bằng $$\log p(x)$$ chính xác với mọi $$K$$, kể cả $$K = 3$$. Quên $$\log K$$, sai dấu $$\log q$$, thiếu hằng
  $$\log 2\pi$$ đều làm lệch con số này.
- Với $$q$$ lệch (mean dịch 0.5, phương sai 1), ELBO trung bình trên 2 000 lần chạy nằm dưới $$\mathcal{L}_{200}$$, và $$\mathcal{L}_{200}$$ không vượt $$\log p(x)$$.

## Bẫy thường gặp

- KL cộng trên chiều latent nhưng tái tạo lấy trung bình trên pixel: tương đương $$\beta$$ rất lớn, posterior collapse (mục 3 lý thuyết).
- Nhầm `logvar` với log std, hoặc với $$\sigma$$.
- Báo $$\mathcal{L}_1$$ là "log-likelihood": đó chỉ là ELBO một mẫu.
