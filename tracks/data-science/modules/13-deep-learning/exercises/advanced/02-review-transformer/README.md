---
title: Transformer encoder tự dựng cho review Olist
level: advanced
services: []
files:
  - path: starter/transformer.py
    note: Positional encoding, multi-head attention, encoder block, classifier
  - path: starter/REPORT.md
    note: Báo cáo so sánh model
  - path: tests/test_transformer.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/13-deep-learning/exercises/advanced/02-review-transformer -q
---

## Mục tiêu

Dựng một Transformer encoder từ các khối cơ bản, kiểm từng khối khớp với PyTorch, rồi đặt nó cạnh
baseline trên dữ liệu thật và trả lời câu hỏi kinh doanh: với review Olist, Transformer train từ đầu
có đáng chi phí không, và nếu không thì cần gì để nó đáng.

## Đề bài

1. Trong `starter/transformer.py` (không dùng `nn.MultiheadAttention` hay
   `nn.TransformerEncoderLayer`; được dùng `F.scaled_dot_product_attention`):
   - `sinusoidal_positional_encoding(max_len, d_model)` theo công thức ở mục 5 của lý thuyết.
   - `MultiHeadSelfAttention(d_model, n_heads, dropout)`: thuộc tính `qkv = nn.Linear(d, 3d)` (hàng xếp
     q, k, v như `in_proj_weight` của PyTorch) và `out = nn.Linear(d, d)`; `key_padding_mask` bool,
     `True` = padding. `ValueError` nếu `d_model` không chia hết cho `n_heads`.
   - `EncoderBlock(d_model, n_heads, d_ff, dropout)`: **pre-LN**,
     `x = x + Dropout(Attn(LN(x)))`, `x = x + Dropout(FFN(LN(x)))`, FFN dùng GELU.
   - `TransformerClassifier(vocab_size, d_model, n_heads, n_layers, d_ff, max_len, dropout)`:
     embedding (`padding_idx=0`) nhân $$\sqrt{d_{model}}$$ cộng positional encoding, các block,
     LayerNorm cuối, trung bình các vị trí không phải padding, `Linear(d_model, 1)`; trả logits `(N,)`.
2. Trên review Olist (dùng `load_reviews`, `time_split`, `build_vocab`, `encode` của bài Intermediate
   03, `max_len = 50`): train classifier (AdamW, early stopping theo val loss), so với TF-IDF + logistic
   regression (unigram và unigram + bigram) và túi embedding. Báo cáo AUC, PR-AUC trên validation và
   test, thời gian train, số tham số, ít nhất 3 seed cho Transformer.
3. Phân tích riêng tập con review có từ "nao" (phủ định): giả thuyết là model nhìn thứ tự từ xử lý
   phủ định tốt hơn túi từ. Dữ liệu có ủng hộ không?
4. Viết `starter/REPORT.md` (ít nhất 400 từ): thiết lập, bảng kết quả, phân tích lỗi (xem vài review
   bị đoán sai nhất), và khuyến nghị cho Olist kèm chi phí.

## Tiêu chí đạt

- Positional encoding đúng công thức; attention khớp `nn.MultiheadAttention` (có và không có
  padding mask) sau khi chép trọng số.
- Encoder block: hoán vị đầu vào thì đầu ra hoán vị theo (không có thông tin vị trí bên trong
  block); padding không ảnh hưởng vị trí thật; khi mọi tham số bằng 0 thì block là hàm đồng nhất
  (pre-LN + residual).
- Classifier: thêm padding không đổi output; đảo thứ tự từ làm đổi output; học được bài toán "token 2
  đứng trước token 3" (túi từ của hai lớp giống hệt nhau) với accuracy trên 90%.
- `REPORT.md` không còn TODO, ít nhất 400 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Shape của attention nhiều head: `qkv(x)` có shape `(B, L, 3d)` → `view(B, L, 3, h, d/h)` →
`permute(2, 0, 3, 1, 4)` cho ba tensor `(B, h, L, d/h)`. Sau attention: `transpose(1, 2)` rồi
`reshape(B, L, d)`. Mask của `F.scaled_dot_product_attention` có quy ước ngược (`True` = được nhìn) và
cần shape broadcast `(B, 1, 1, L)`.

### Gợi ý 2

Trên CPU, một epoch với `d_model = 64`, 2 block, khoảng 18 nghìn review mất cỡ chục giây. Bắt đầu
với `lr = 1e-3`, `weight_decay = 0.01`, dropout 0.1, batch 128, patience 2. Positional encoding nên là
`register_buffer` (đi theo model khi `.to(device)`, không phải tham số train).
