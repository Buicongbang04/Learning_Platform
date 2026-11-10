# Lời giải: autoencoder và VAE trên MNIST

## Cách làm

**Hai model.** Autoencoder: `encoder = Linear(784, 512) → ReLU → Linear(512, d)`, `decoder = Linear(d, 512) → ReLU → Linear(512, 784)`.
VAE: phần thân encoder dừng ở tầng ẩn, hai đầu tuyến tính `fc_mu`, `fc_logvar`; `forward` lấy $$\varepsilon$$ bằng một lần
`torch.randn(mu.shape, generator=...)` rồi $$z = \mu + e^{\text{logvar}/2}\varepsilon$$. Decoder trả logits: likelihood Bernoulli tính bằng
`binary_cross_entropy_with_logits` (ổn định số, mục 2 module 01).

**Thang đo của loss.** `recon` = BCE với `reduction="none"`, `.sum(1)` trên pixel, `.mean()` trên batch; `kl` cộng trên chiều latent rồi trung
bình trên batch. Cả hai cùng đơn vị nats mỗi ảnh nên cộng được. Dùng `reduction="mean"` mặc định làm tái tạo nhỏ đi 784 lần, tương đương
$$\beta = 784$$: test so từng con số với bản tham chiếu nên bắt được.

**Vòng train.** Adam lr 1e-3, batch 128, xáo bằng `torch.randperm(N, generator=g)` với `g` seed `seed` trên CPU; cùng generator (hoặc một
generator CUDA cùng seed khi train trên GPU) đưa vào `loss_fn` để lấy $$\varepsilon$$. Loss epoch là tổng `loss.item() * len(xb)` chia $$N$$: với
60 000 ảnh và batch 128, batch cuối có 96 ảnh, trung bình các batch sẽ lệch nhẹ. Kết thúc `model.eval()`.

**`iwae_nll`.** Mỗi batch ảnh: `mu, logvar = encode(x)`, $$\varepsilon$$ shape `(K, B, d)`, $$z = \mu + \sigma\varepsilon$$, decode cả `(K, B, d)` một lần (Linear
nhận chiều đầu bất kỳ). Ba log-mật độ:

$$
\log p(x \mid z_k) = -\mathrm{BCE}_{\text{sum}},\quad \log p(z_k) = -\tfrac12\sum(z_k^2 + \log 2\pi),\quad \log q(z_k \mid x) = -\tfrac12\sum(\varepsilon_k^2 + \text{logvar} + \log 2\pi)
$$

rồi `logsumexp` trên chiều $$K$$ trừ $$\log K$$. Bọc trong `torch.no_grad()`. Test so với **tích phân số** trên một VAE latent 1 chiều (lưới 6 001
điểm trên $$[-9, 9]$$): với $$q = \mathcal{N}(0, 4)$$ rộng hơn posterior, $$K = 4000$$ khớp tới 0.05 nats. Thiếu $$\log q$$, thiếu $$\log p(z)$$ hay quên
trừ $$\log K$$ đều lệch hàng nats.

**`active_units`.** Mean encoder của mọi ảnh, phương sai theo trục ảnh (chia $$N$$), đếm chiều vượt ngưỡng 0.01. Test làm hai chiều có
`fc_mu` bằng 0 (mean không đổi theo ảnh) trong khi `fc_logvar` thay đổi mạnh: chiều đó vẫn chết, vì thông tin truyền qua mean.

## Kết quả thật

CPU, `OMP_NUM_THREADS=4`, torch 2.14.1, seed 0, 20 epoch mỗi model, đo trên 10 000 ảnh test MNIST (pixel xám trong $$[0, 1]$$, 81.5% pixel
đúng bằng 0 hoặc 1). Train mỗi model khoảng 45 giây, cả notebook 5 phút.

| Model | Tái tạo | KL | $$-\text{ELBO}$$ | $$-\mathcal{L}_{100}$$ | Active units |
| --- | --- | --- | --- | --- | --- |
| AE-16 | 69.1 | | | | |
| VAE-16, $$\beta$$ 0.5 | 74.5 | 30.6 | 105.1 | | 16/16 |
| VAE-16, $$\beta$$ 1 | 79.7 | 23.8 | **103.5** | **99.8** (0.184 bits/dim) | 16/16 |
| VAE-16, $$\beta$$ 4 | 107.7 | 9.8 | 117.5 | | 12/16 |
| VAE-16, $$\beta$$ 10 | 144.1 | 3.8 | 147.9 | | 6/16 |
| VAE-2, $$\beta$$ 1 | 144.8 | 5.9 | 150.7 | | |

Mẫu sinh từ $$z \sim \mathcal{N}(0, I)$$, 1 000 mẫu, chấm bằng một MLP classifier 2 epoch (test accuracy 0.960):

| Nguồn | Tỉ lệ classifier tự tin > 0.9 | Số lớp xuất hiện |
| --- | --- | --- |
| Ảnh thật (test) | 0.839 | 10 |
| AE-16 | **0.000** | 9 |
| VAE-16, $$\beta$$ 1 / 0.5 / 4 / 10 | 0.334 / 0.269 / 0.406 / 0.409 | 10 |

Kernel `ai-gpu` (PC) cho cùng bức tranh với số lệch nhẹ (chuỗi số ngẫu nhiên khác): AE 69.0; VAE recon 80.0, KL 23.6, $$-\mathcal{L}_1$$ 103.6, $$-\mathcal{L}_{100}$$ 99.7;
$$\beta$$ 4 và 10 còn 12 và 6 active units; mẫu VAE tự tin 0.308 ($$\beta = 1$$) và 0.410 ($$\beta = 10$$); AE vẫn 0.000. Cả notebook khoảng 7 phút.

Đọc kết quả:

- **Tái tạo và sinh là hai mục tiêu khác nhau.** AE tái tạo tốt hơn VAE 10.6 nats/ảnh nhưng không sinh được: std mã AE theo từng chiều từ 2.98
  tới 4.30, nên $$z \sim \mathcal{N}(0, I)$$ rơi vào vùng chỉ chiếm một phần nhỏ của các mã thật, decoder chưa từng thấy; không mẫu nào được classifier
  nhận ra chắc chắn, và histogram lệch hẳn về vài lớp.
- **ELBO là cận dưới khá lỏng.** $$-\mathcal{L}_1 = 103.5$$ nhưng $$-\mathcal{L}_{100} = 99.8$$: 3.7 nats là khoảng hở do posterior Gauss đường chéo. So với mốc
  206.0 nats của model Bernoulli độc lập từng pixel (mục 1 lý thuyết), VAE nhỏ này đã bắt được phần lớn tương quan giữa các pixel.
- **β là núm đánh đổi.** $$\beta = 1$$ cho ELBO tốt nhất (đúng thứ nó tối ưu). $$\beta = 10$$ giết 10/16 chiều, tái tạo tệ gần gấp đôi, nhưng mẫu sinh lại "rõ"
  hơn theo classifier (0.409 so với 0.334): latent bị ép gọn nên ít vùng trống, đổi lại mẫu đơn điệu hơn. "Posterior collapse" ở đây không
  phải bug mà là hệ quả trực tiếp của trọng số KL; nó thành bug khi bạn không cố ý chọn trọng số đó (ví dụ `reduction="mean"`).
- Latent 2 chiều (hình trong notebook) cho thấy các chữ số thành cụm liền nhau, và lưới decode chuyển dần giữa các chữ số: đó là "không lỗ"
  mà KL mua được. Nội suy giữa hai mã AE đi qua các ảnh nhoè không giống chữ số nào; giữa hai mean VAE thì chuyển mượt hơn.

## Bẫy thường gặp

- `reduction="mean"` trong BCE: posterior collapse gần như toàn bộ, mẫu sinh là một ảnh trung bình.
- Đánh giá `-ELBO` hay `iwae_nll` ở chế độ train với dropout (ở đây không có dropout, nhưng thói quen gọi `eval()` vẫn cần).
- Báo "log-likelihood" của VAE bằng ELBO một mẫu; so con số với paper dùng MNIST nhị phân hoá (khác dữ liệu).
- Số liệu thay đổi vài phần trăm theo device (CPU và GPU dùng chuỗi số ngẫu nhiên khác nhau) và số luồng BLAS; thứ bậc giữ nguyên.
