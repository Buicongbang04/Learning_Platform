---
title: Xavier, He, SGD momentum, Adam/AdamW khớp torch.optim
level: intermediate
services: []
files:
  - path: starter/optim.ipynb
    note: 2 hàm, 2 lớp TODO
  - path: tests/test_optim.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py mnist
  - uv run jupyter lab tracks/ai-engineer/modules/01-nn-from-scratch/exercises/intermediate/02-init-and-optimizers/starter/optim.ipynb
  - uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/intermediate/02-init-and-optimizers -q
---

## Mục tiêu

Tự viết khởi tạo Xavier, He và hai optimizer dùng nhiều nhất (SGD momentum, Adam/AdamW) bằng numpy, khớp
`torch.optim` tới từng bước. Rồi tái hiện hai bảng của phần lý thuyết: vanishing/exploding qua 10 tầng
(mục 5) và năm cấu hình optimizer trên MNIST (mục 6), để thấy bằng số vì sao chọn khởi tạo và lr có cơ sở.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Mở `starter/optim.ipynb`. Cell đầu (tag `explore`) tải MNIST vào `data/raw/mnist` nếu chưa có.

1. `xavier_init(fan_in, fan_out, rng)` và `he_init(fan_in, fan_out, rng)`: ma trận `(fan_in, fan_out)`
   phân phối chuẩn, trung bình 0, phương sai lần lượt $$\frac{2}{n_{in} + n_{out}}$$ và $$\frac{2}{n_{in}}$$; số ngẫu nhiên chỉ lấy
   từ `rng`.
2. `SGDMomentum(lr, momentum)`: kiểu PyTorch $$v \leftarrow \mu v + g,\ \theta \leftarrow \theta - \eta v$$.
3. `Adam(lr, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0)`: Adam có bias correction; `weight_decay > 0`
   là AdamW (trừ thẳng $$\eta\lambda\theta$$ vào tham số trước bước Adam, không cộng vào gradient).

Cả hai optimizer có `step(params)`, với `params` là danh sách cặp `(tham số, gradient)` (giống
`MLP.params()` của bài 01), cập nhật tham số **tại chỗ**, giữ state riêng cho từng tham số.

Rồi chạy các cell `explore`: bảng std activation qua 10 tầng 512 neuron với năm cách khởi tạo, và năm
optimizer trên MLP 784-128-10 (MNIST, 3 epoch). Cả notebook chạy khoảng 10 giây. Sau đó làm phần trắc
nghiệm của bài trong app.

## Tiêu chí đạt

- `he_init(1000, 1000)` có phương sai $$2/1000$$ (sai lệch dưới 5%), `he_init(1000, 10)` vẫn $$2/1000$$ (dùng
  `fan_in`); `xavier_init(1000, 500)` có phương sai $$2/1500$$; cùng seed cho cùng ma trận.
- 20 bước trên hàm bậc hai hai tham số khớp `torch.optim.SGD` (momentum 0 và 0.9) và `torch.optim.AdamW`
  (`weight_decay` 0 và 0.1, hai bộ `betas`) với `atol=1e-6`.
- Với gradient 0, AdamW co tham số đúng hệ số $$1 - \eta\lambda$$, Adam thuần đứng yên; bước Adam đầu tiên đi
  đúng `lr` theo dấu gradient, dù gradient lớn hay nhỏ.
- Cell `explore` in ra hai bảng ở mục 5 và 6 lý thuyết (vd. "ReLU, He": std gradient về input
  9.75e-01; Adam lr 1e-3: test acc 0.9747; máy khác có thể lệch ở chữ số thứ tư).

## Gợi ý

### Gợi ý 1

`rng.normal(loc, scale, size)` nhận **độ lệch chuẩn**, không phải phương sai. State của optimizer là một
danh sách mảng `np.zeros_like(p)` tạo ở lần `step` đầu; vì `params` luôn cùng thứ tự, phần tử thứ i của
state thuộc về tham số thứ i. Bias correction cần biết đây là bước thứ mấy, đếm từ 1.

### Gợi ý 2

Để khớp PyTorch, cập nhật state tại chỗ theo đúng thứ tự: `m = β1·m + (1 − β1)·g`,
`v = β2·v + (1 − β2)·g²`, rồi `m̂ = m / (1 − β1^t)`, `v̂ = v / (1 − β2^t)`, rồi
`p -= lr · m̂ / (sqrt(v̂) + eps)`; `eps` cộng **sau** căn. Với AdamW, nhân `p` với `1 − lr·λ` trước tất cả.
