# Lời giải: scaled dot-product attention

## Cách làm

Bốn dòng:

```python
scores = q @ k.transpose(-2, -1) / math.sqrt(q.size(-1))
if mask is not None:
    scores = scores.masked_fill(~mask, float("-inf"))
weights = torch.softmax(scores, dim=-1)
return weights @ v, weights
```

`causal_mask` là `tril` của ma trận toàn `True`; `padding_mask` là
`torch.arange(max_len)[None, :] < lengths[:, None]`. Để che theo key cho mọi query, thêm một chiều:
`padding_mask(...)[:, None, :]` có shape `(B, 1, Lk)` và broadcast lên `(B, Lq, Lk)`. Kết hợp cả hai
loại mask bằng phép `&`.

## Vì sao chia cho căn bậc hai của d_k

Nếu các thành phần của q và k độc lập, trung bình 0, phương sai 1, thì tích vô hướng
$$q^\top k = \sum_{i=1}^{d_k} q_i k_i$$ có phương sai $$d_k$$. Với $$d_k = 64$$, điểm số dao động cỡ ±8 đến
±16, softmax gần như one-hot, và gradient qua softmax gần 0 ở mọi vị trí trừ một: model học rất
chậm. Chia cho $$\sqrt{d_k}$$ đưa phương sai về 1, giữ softmax ở vùng có gradient. Chia cho $$d_k$$ thì
ngược lại: phương sai $$1/d_k$$, softmax gần đều, attention không "chọn" được gì.

## Vì sao dùng −inf chứ không phải −1e9

Với −1e9, trọng số ở vị trí bị che là $$e^{-10^9}$$, bằng 0 trong float32, nên thường không sao. Nhưng
trong float16 (mixed precision) −1e9 tràn thành −inf hoặc gây `nan` tuỳ cách cộng; nhiều codebase
dùng `torch.finfo(dtype).min` vì lý do đó. −inf chỉ có một rủi ro: một hàng bị che **toàn bộ**
(query là padding) thì softmax ra `nan`. Cách xử lý thông thường: không che query, chỉ che key, và
bỏ output ở vị trí padding khi pooling (bài Advanced 02).

## Bẫy thường gặp

- `k.T` trên tensor nhiều chiều: `.T` đảo **mọi** chiều, không chỉ hai chiều cuối (PyTorch đã cảnh
  báo deprecated). Dùng `transpose(-2, -1)` hoặc `mT`.
- Nhầm quy ước mask: `nn.MultiheadAttention` dùng `key_padding_mask` với `True` = **bị che**,
  ngược với `attn_mask` bool của `F.scaled_dot_product_attention`. Luôn đọc docstring.
- Softmax theo trục query (`dim=-2`) thay vì trục key: shape vẫn đúng, kết quả sai.
- Ở production, dùng `F.scaled_dot_product_attention`: nó chọn kernel FlashAttention hoặc
  memory-efficient khi có GPU, không tạo ma trận $$L \times L$$ đầy đủ trong bộ nhớ.
