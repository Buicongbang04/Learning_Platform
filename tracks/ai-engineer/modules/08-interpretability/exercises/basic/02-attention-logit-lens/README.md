---
title: Chấm điểm head attention, logit lens và direct logit attribution
level: basic
services: []
files:
  - path: starter/lens.py
    note: 7 hàm TODO
  - path: tests/test_lens.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/08-interpretability/exercises/basic/02-attention-logit-lens -q
---

## Mục tiêu

Viết các phép đo "đọc" model mà không can thiệp: điểm previous-token, duplicate-token và induction của từng head trên dãy ngẫu
nhiên lặp lại, logit lens (đọc residual stream giữa chừng ra vocab) và direct logit attribution (mỗi thành phần của residual
stream đẩy logit đúng lên bao nhiêu). Bài Intermediate 01 dùng chúng để tìm induction head trong GPT-2 small.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 3 và 4 phần lý thuyết. Model là lớp `GPT` của module 05 (pre-norm, `ln_f` rồi `lm_head` dùng chung trọng số với
`tok_emb`). `pattern` là ma trận attention sau softmax shape `(B, n_head, T, T)`, hàng là vị trí query, cột là vị trí key, như
`pattern.l` của bài Basic 01. Trong `starter/lens.py`:

1. `repeated_tokens(vocab_size, half, batch, generator, prefix=None)`: dãy `[prefix] + r + r`.
2. `prev_token_score(pattern)`, `induction_score(pattern, half)`, `duplicate_token_score(pattern, half)`: mỗi hàm trả một số
   cho mỗi head (shape `(n_head,)`), là attention trung bình đặt vào đúng vị trí key mà loại head đó nhắm tới. Định nghĩa
   chính xác ở docstring.
3. `logit_lens(model, resid)` và `token_rank(logits, targets)`.
4. `direct_logit_attribution(model, components, final_resid, direction)`: đóng góp tuyến tính của từng thành phần vào
   `ln_f(final_resid) @ direction`, với thang của LayerNorm cuối giữ cố định.

## Tiêu chí đạt

- `repeated_tokens` đúng shape, nửa sau trùng nửa đầu, đúng chuỗi ngẫu nhiên của `generator`, `prefix` ở đầu.
- Ba hàm điểm head cho đúng 1 với head "lý tưởng" của loại đó và 0 với head loại khác, trên pattern dựng tay có hoặc không có
  token đầu; chỉ lấy trung bình trên các vị trí query đúng định nghĩa.
- `logit_lens` ở stream cuối bằng logits của model; ở stream bất kỳ khớp đường đi của model; không gradient.
- `token_rank` đúng với logit hoà và tensor nhiều chiều.
- Tổng `direct_logit_attribution` trên mọi thành phần cộng `ln_f.bias @ direction` bằng đúng chênh lệch logit; đóng góp tuyến
  tính theo từng thành phần.

## Gợi ý

### Gợi ý 1

`tensor.diagonal(offset, dim1, dim2)` lấy một đường chéo của hai trục cuối mà không cần vòng lặp. Với `induction_score`, vẽ ra
giấy một dãy `[p] a b c a b c` (half = 3): ở vị trí của chữ `b` thứ hai, head induction nhìn vào đâu?

### Gợi ý 2

LayerNorm là $$\frac{x - \mu(x)}{\sigma(x)}\gamma + \beta$$. Nếu coi $$\sigma$$ là hằng số (lấy từ stream cuối), phần còn lại tuyến
tính theo $$x$$, và trừ trung bình cũng tuyến tính, nên đóng góp của tổng bằng tổng các đóng góp. Kiểm hàm của bạn bằng đúng tính
chất đó trước khi chạy test.
