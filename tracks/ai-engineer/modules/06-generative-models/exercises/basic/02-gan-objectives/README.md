---
title: Hàm mục tiêu của GAN, JS divergence và gradient penalty
level: basic
services: []
files:
  - path: starter/gan.py
    note: 8 hàm TODO
  - path: tests/test_gan.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/06-generative-models/exercises/basic/02-gan-objectives -q
---

## Mục tiêu

Viết các hàm mục tiêu của GAN bằng logits cho đúng và ổn định số, kiểm bằng số định lý trung tâm của Goodfellow (2014): với
discriminator tối ưu, giá trị của trò chơi bằng $$-\log 4 + 2\,\mathrm{JS}$$. Thấy tận mắt vì sao loss minimax gốc làm generator hết
gradient, viết gradient penalty của WGAN-GP, và một thước đo mode collapse trên dữ liệu đồ chơi mà bài Intermediate 02 dùng.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 4 phần lý thuyết. Trong `starter/gan.py`, discriminator trả **logit** $$l$$, $$D = \sigma(l)$$; loss là trung bình theo batch, để minimize.

1. `d_loss(real_logits, fake_logits)`: $$-\big[\overline{\log D(x)} + \overline{\log(1 - D(G(z)))}\big]$$ (hai trung bình, cộng lại).
2. `g_loss_saturating(fake_logits)`: $$\overline{\log(1 - D(G(z)))}$$; `g_loss_nonsaturating(fake_logits)`: $$-\overline{\log D(G(z))}$$. Cả ba hàm
   ổn định khi logit cỡ ±200.
3. `optimal_discriminator(p_data, p_g)`: $$D^* = p_{data}/(p_{data} + p_g)$$ trên từng ô của hai histogram; ô mà cả hai bằng 0 thì 0.5.
4. `js_divergence(p, q)`: Jensen-Shannon theo nats, quy ước $$0\log 0 = 0$$.
5. `gan_value(p_data, p_g, d)`: $$V = \sum p_{data}\log D + \sum p_g\log(1 - D)$$ trên histogram, quy ước $$0\log 0 = 0$$.
6. `gradient_penalty(critic, real, fake, alpha)`: $$\hat x = \alpha\,x_{real} + (1 - \alpha)\,x_{fake}$$ với `alpha` shape `(B,)` (broadcast theo
   mọi chiều còn lại), trả trung bình $$(\lVert\nabla_{\hat x}\,\text{critic}(\hat x)\rVert_2 - 1)^2$$ (norm theo từng mẫu, gộp mọi chiều trừ batch).
   Kết quả phải backward được về tham số của critic.
7. `mode_coverage(samples, centers, std, min_count=10)`: mẫu "chất lượng cao" cách tâm gần nhất dưới $$3\cdot$$`std`; một mode được phủ
   khi có ít nhất `min_count` mẫu chất lượng cao gán về nó. Trả `(số mode được phủ, tỉ lệ mẫu chất lượng cao)`, kiểu `int`, `float`.

## Tiêu chí đạt

- `d_loss` bằng binary cross-entropy với nhãn 1/0, bằng $$2\log 2$$ khi mọi logit bằng 0; hai loss của G đúng công thức, hữu hạn ở ±200.
- Tại logit giả -8: gradient của bản saturating có trị tuyệt đối dưới 1e-3, bản non-saturating bằng $$-(1 - \sigma(-8))$$.
- $$D^*$$ đúng (kể cả ô trống), JS đúng công thức, bằng 0 khi hai phân phối trùng và bằng $$\log 2$$ khi rời nhau;
  `gan_value(p, q, D*)` $$= -\log 4 + 2\,\mathrm{JS}(p\,\|\,q)$$ trên 3 cặp histogram, và D khác $$D^*$$ cho giá trị nhỏ hơn.
- Gradient penalty của critic tuyến tính $$w^\top x$$ bằng $$(\lVert w\rVert - 1)^2$$ và có gradient đúng theo $$w$$; với critic $$\tfrac12\lVert x\rVert^2$$ đo đúng
  tại điểm nội suy.
- `mode_coverage` đếm 8/8 với dữ liệu đủ mode, 3/8 khi chỉ có 3 mode, 0 khi mẫu nằm xa mọi tâm, và tôn trọng `min_count`.

## Gợi ý

### Gợi ý 1

Mọi $$\log\sigma(\cdot)$$ và $$\log(1 - \sigma(\cdot))$$ viết được bằng `F.softplus` (bài Basic 01 dùng cùng mẹo). Với $$0\log 0$$, `torch.where` trên
mặt nạ $$p > 0$$ là đủ, nhưng nhớ rằng nhánh không được chọn của `where` vẫn được tính: tránh để nó ra `nan` (kẹp trước khi `log`).

### Gợi ý 2

`torch.autograd.grad(outputs, inputs, create_graph=True)` trả gradient theo input mà vẫn giữ graph, nên penalty là một hàm khả vi của tham số
critic. $$\hat x$$ cần `requires_grad_(True)`. Với mode coverage, `torch.cdist` cho ma trận khoảng cách mẫu–tâm, `torch.bincount` đếm theo tâm.
