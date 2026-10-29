---
title: Scaled dot-product attention từ đầu
level: basic
services: []
files:
  - path: starter/attention.py
    note: 3 hàm TODO
  - path: tests/test_attention.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/13-deep-learning/exercises/basic/03-attention -q
---

## Mục tiêu

Tự viết phép toán trung tâm của Transformer, gồm cả hai loại mask (causal và padding), và kiểm nó
khớp tới từng số với `torch.nn.functional.scaled_dot_product_attention`. Sau bài này bạn đọc được
mọi biến thể attention trong paper mà không phải đoán shape.

## Đề bài

Trong `starter/attention.py`, theo đúng quy ước mask của PyTorch (bool, `True` = được nhìn):

1. `scaled_dot_product_attention(q, k, v, mask=None) -> (output, weights)`: công thức ở mục 5 của
   lý thuyết,
   $$\mathrm{Attention}(Q, K, V) = \mathrm{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$.
   Nhận mọi số chiều batch phía trước (`(..., L, d)`), trả cả ma trận trọng số `(..., Lq, Lk)`.
   Vị trí bị che phải có trọng số **đúng bằng 0**.
2. `causal_mask(length)`: ma trận bool tam giác dưới, query `i` chỉ nhìn key `j <= i`.
3. `padding_mask(lengths, max_len)`: `(B, max_len)`, `True` ở vị trí thật, `False` ở padding.

Không gọi `F.scaled_dot_product_attention` hay `nn.MultiheadAttention` (test chặn hàm này khi
chạy code của bạn ở một test).

## Tiêu chí đạt

- Khớp `F.scaled_dot_product_attention` (float64) khi không mask, với causal mask, và với padding
  mask; trọng số mỗi hàng cộng lại bằng 1.
- Trọng số đúng là softmax của điểm chia cho $$\sqrt{d_k}$$.
- Với causal mask, đổi token tương lai không làm đổi output ở các vị trí trước đó.
- Với padding mask, ghi rác vào `v` ở vị trí padding không làm đổi output.
- Điểm số cỡ $$10^4$$ (float32) không sinh `nan` hay `inf`.
- Gradient theo q, k, v khớp PyTorch.

## Gợi ý

### Gợi ý 1

`k.transpose(-2, -1)` đổi hai chiều cuối, giữ nguyên các chiều batch; `@` tự broadcast. Che bằng
`scores.masked_fill(~mask, float("-inf"))` trước softmax: $$e^{-\infty} = 0$$ nên trọng số đúng
bằng 0, không phải "rất nhỏ" như khi cộng −1e9.

### Gợi ý 2

`torch.softmax` đã trừ max của mỗi hàng trước khi lấy mũ nên không tràn số. Nếu tự viết softmax,
hãy trừ `scores.amax(-1, keepdim=True)` trước. `causal_mask`: `torch.ones(L, L, dtype=torch.bool).tril()`.
`padding_mask`: so sánh `torch.arange(max_len)` với `lengths` sau khi thêm chiều để broadcast.
