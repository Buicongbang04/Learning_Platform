# Lời giải: RoPE, RMSNorm, SwiGLU, GQA và KV cache

## Cách làm

| Thành phần | Cài đặt | Ghi chú |
| --- | --- | --- |
| `RMSNorm` | `x * rsqrt(mean(x²) + eps) * weight` | bỏ trừ trung bình và bias của LayerNorm: ít phép tính hơn, chất lượng tương đương (Zhang, Sennrich 2019) |
| `rope_cache` | `inv_freq = base ** (-arange(0, d, 2) / d)`, `angles = outer(pos, inv_freq)`, nối `[angles, angles]` | tính bằng float64 rồi ép float32: góc ở vị trí lớn (vài nghìn rad) mất chính xác nếu tính float32 |
| `rotate_half` | `x1, x2 = x.chunk(2, -1)`, trả `cat([-x2, x1])` | |
| `apply_rope` | `x * cos[s:s+T] + rotate_half(x) * sin[s:s+T]` | với cột $$i < d/2$$: $$x_i\cos - x_{i+d/2}\sin$$; cột $$i + d/2$$: $$x_{i+d/2}\cos + x_i\sin$$ |
| `repeat_kv` | `x[:, :, None].expand(B, H, r, T, D).reshape(B, H*r, T, D)` | `expand` không chép bộ nhớ; `reshape` chép một lần |
| `SwiGLU` | `w2(silu(w1 x) * w3 x)` | |
| `GQAttention` | xem dưới | |
| `kv_cache_bytes` | $$2 \cdot L \cdot H_{kv} \cdot d \cdot T \cdot B \cdot \text{bytes}$$ | hệ số 2 vì có cả K và V |

`GQAttention.forward(x, cache)`:

1. Chiếu q `(B, H, T, d)`, k, v `(B, H_kv, T, d)`.
2. $$P$$ = số token trong cache (`cache[0].shape[2]`, bằng 0 khi không có cache). Quay q và k với `start_pos = P`. K trong
   cache đã quay theo vị trí của nó, không quay lại.
3. Nối k, v với cache; `new_cache = (k, v)` lúc này, **trước** `repeat_kv`: cache chỉ lưu $$H_{kv}$$ head, đó là toàn bộ lợi
   ích bộ nhớ của GQA.
4. `repeat_kv` lên $$H$$ head, score `(B, H, T, P+T)`, mask `ones(T, P+T).tril(diagonal=P)`, softmax (float32), nhân v, `wo`.

## Kiểm bằng gì

- RoPE được kiểm bằng **tính chất**, không chỉ bằng giá trị: giữ độ dài (phép quay), và
  $$\langle R_{10} q, R_3 k\rangle = \langle R_{40} q, R_{33} k\rangle$$. Tính chất thứ hai là lý do RoPE tồn tại: attention score
  chỉ phụ thuộc khoảng cách tương đối, dù mỗi vector được mã hoá theo vị trí tuyệt đối.
- Một test tính tay một vector 4 chiều ở vị trí 1 bắt được quy ước ghép cặp sai (liền kề thay vì nửa-nửa), dấu sai, tần
  số sai. Lưu ý: dùng quy ước liền kề cho **cả** q và k vẫn cho model đúng về mặt toán (tính chất tương đối vẫn giữ), nhưng
  nạp trọng số Llama đã train theo quy ước nửa-nửa vào code quy ước liền kề thì model hỏng: đây là bug có thật khi
  chuyển checkpoint giữa Meta và Hugging Face (HF hoán vị hàng của `wq`, `wk` lúc chuyển).
- So với bản tham chiếu `repeat_interleave` + `F.scaled_dot_product_attention` bắt `repeat` sai thứ tự (head 1 dùng kv
  head 1 thay vì 0).
- Decode có cache so với forward đầy đủ, cả từng token lẫn prefill hai khúc, bắt ba lỗi hay gặp: quên `start_pos` (mọi
  token mới quay như vị trí 0), mask không dịch (token mới không thấy token cũ trong cùng khúc), lưu cache sau
  `repeat_kv`.

## Bẫy thường gặp

- Áp RoPE lên v: vô hại về hình thức, nhưng không còn là RoPE (v không tham gia score).
- Tính `cos`, `sin` mỗi lần forward: đúng nhưng tốn; cache sẵn tới `max_len`, cắt theo vị trí.
- Mask `tril()` không dịch khi có cache: với ma trận `T × (P+T)`, `tril(diagonal=0)` chỉ mở $$t + 1$$ cột **đầu**, tức token
  mới nhìn các token cũ đầu tiên thay vì mọi token cũ. Một số bản cài bỏ hẳn mask khi `T = 1` (một token mới được nhìn
  mọi thứ, đúng) rồi quên rằng prefill nhiều token vào cache có sẵn (chat nhiều lượt) cần mask dịch $$P$$ cột.
- `kv_cache_bytes` quên hệ số 2 (K và V) hoặc dùng `n_head` thay `n_kv_head`: với Llama 3 8B sai 2 lần hoặc 4 lần.
