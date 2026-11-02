# Lời giải: Mixture-of-Experts và state space model chọn lọc

## MoE

- `route`: `logits = gate(x)`, `top_logits, top_idx = logits.topk(k)`, `weights = softmax(top_logits)`,
  `probs = softmax(logits)`. Đây là cách của Mixtral (softmax sau khi chọn, trọng số luôn cộng lại bằng 1). Switch
  Transformer và DeepSeek dùng softmax (hoặc sigmoid) trên mọi expert rồi lấy k giá trị lớn nhất **không** chuẩn hoá lại;
  hai cách cho cùng thứ tự chọn nhưng khác độ lớn trọng số, test phân biệt được.
- `forward`: phẳng hoá, với mỗi expert lấy `token, slot = (top_idx == e).nonzero(as_tuple=True)`, chạy expert trên
  `x[token]`, nhân `weights[token, slot]`, `out.index_add_(0, token, ...)`. Mỗi token đi qua đúng k expert: số phép tính
  mỗi token bằng k lần một MLP dù có `n_experts` bộ trọng số.
- Router học được vì `weights` là hàm khả vi của logit (top-k chỉ chọn **chỉ số**, giá trị vẫn có gradient). Nếu chỉ dùng
  chỉ số (`argmax`, trọng số 1) thì router chỉ học được từ loss cân tải.
- `load_balancing_loss`: $$\mathcal{L}_{aux} = E \sum_i f_i P_i$$ với $$f_i$$ là tỉ lệ lượt chọn (không khả vi) và $$P_i$$ là
  xác suất trung bình (khả vi). Gradient đi qua $$P_i$$ và đẩy xác suất của expert đang quá tải xuống. Chia cho $$N k$$ (tổng
  lượt chọn) chứ không chia $$N$$, để giá trị lý tưởng là 1 với mọi k.

## SSM

| Hàm | Cài đặt |
| --- | --- |
| `discretize` | `A_bar = exp(Δ·A)`, `B_bar = (A_bar - 1) / A · B` |
| `ssm_scan` | `h = A_bar[t] * h + B_bar[t] * x[t, :, None]`; `y[t] = (h * C[t]).sum(-1)` |
| `ssm_kernel` | `(A_bar[None] ** arange(L)[:, None, None] * B_bar * C).sum(-1)` |
| `causal_conv` | `y[k:] += kernel[k] * x[:T-k]` với k = 0..T-1 |
| `selective_scan` | `discretize(A[None], B[:, None, :], Δ[:, :, None])`, rồi `ssm_scan(..., C[:, None, :], x)` |

Zero-order hold là nghiệm đúng của $$h'(t) = A h + B x$$ khi $$x$$ giữ hằng trong khoảng Δ; Euler ($$\bar A = 1 + \Delta A$$)
chỉ đúng khi Δ nhỏ và mất ổn định khi $$\Delta |A| > 2$$. Bản Mamba gốc dùng ZOH cho A và rút gọn $$\bar B \approx \Delta B$$;
bài này dùng ZOH cho cả hai để có đáp án chính xác (test phân biệt hai cách).

Ba tính chất test kiểm chính là ba ý của mục 6 lý thuyết:

1. **Bất biến theo thời gian = tích chập.** Khi $$\bar A, \bar B, C$$ không đổi theo $$t$$, mở hồi quy ra được
   $$y_t = \sum_{k} (C \bar A^k \bar B) x_{t-k}$$: train song song như CNN (S4 tính kernel bằng FFT), inference như RNN
   (trạng thái $$h$$ cỡ cố định $$D \times N$$).
2. **Chọn lọc.** Mamba cho Δ, B, C phụ thuộc token: Δ lớn thì $$\bar A \to 0$$ (quên hết, nạp token mới), Δ = 0 thì
   $$\bar A = 1, \bar B = 0$$ (bỏ qua token, giữ trạng thái). Đây là "cổng" giống LSTM, nhưng tuyến tính theo $$h$$ nên vẫn
   quét song song được (parallel scan). Cái giá: hết là tích chập.
3. **Nhân quả**, trạng thái cố định: sinh token thứ 10 000 tốn đúng như token thứ 10, không có KV cache.

## Bẫy thường gặp

- Chạy mọi expert trên mọi token rồi nhân mask 0: đúng kết quả, nhưng mất toàn bộ lợi ích tính toán của MoE (test đếm
  số hàng mỗi expert nhận).
- Chia $$f_i$$ cho $$N$$ thay vì $$N k$$: với top-2, loss lý tưởng thành 2.
- Ghi $$y_t$$ trước khi cập nhật $$h_t$$: lệch một bước, token hiện tại không ảnh hưởng output của chính nó.
- Kernel bắt đầu từ $$\bar A^1$$: mất số hạng $$k = 0$$ (đường thẳng từ $$x_t$$ tới $$y_t$$).
