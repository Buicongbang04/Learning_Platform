---
title: LSTM forward và BPTT bằng numpy, khớp nn.LSTM
level: basic
services: []
files:
  - path: starter/lstm.py
    note: 1 lớp, 1 hàm sigmoid, 1 hàm clip, 5 chỗ TODO
  - path: tests/test_lstm.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/basic/03-lstm-numpy -q
---

## Mục tiêu

Tự viết một tầng LSTM bằng numpy, cả forward qua thời gian lẫn backpropagation through time, khớp `torch.nn.LSTM`
tới `1e-10`, cộng gradient clipping theo chuẩn toàn cục. Làm xong bạn đọc được mọi phương trình trong `nn.LSTM`, và
thấy bằng số con đường cộng của cell state giữ gradient qua 50 bước.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Trong `starter/lstm.py` (chỉ numpy, float64), phương trình và thứ tự cổng `i, f, g, o` như mục 5 phần lý thuyết:
$$z_t = W_{ih} x_t + b_{ih} + W_{hh} h_{t-1} + b_{hh}$$, 4 khối $$H$$ dòng liền nhau.

1. `sigmoid(x)`: ổn định số với `|x|` cỡ $$10^4$$ (không cảnh báo tràn).
2. `LSTM(input_size, hidden_size, rng)`: `W_ih (4H, D)`, `W_hh (4H, H)`, `b_ih (4H,)`, `b_hh (4H,)`, khởi tạo đều
   $$U(-1/\sqrt{H}, 1/\sqrt{H})$$ như PyTorch, lấy từ `rng.uniform` theo đúng thứ tự `W_ih`, `W_hh`, `b_ih`, `b_hh`.
3. `forward(x, h0=None, c0=None)`: `x` shape `(T, N, D)`, trả `(out, (h_T, c_T))` với `out` shape `(T, N, H)`; state đầu
   mặc định bằng 0. Lưu những gì backward cần.
4. `backward(dout, dh_T=None, dc_T=None)`: `dout` là $$\partial L/\partial\,\text{out}$$, `dh_T`, `dc_T` là gradient thêm
   vào state cuối (ví dụ khi state cuối đi tiếp vào một lớp khác). Trả `dx` shape `(T, N, D)` và **gán** `dW_ih`,
   `dW_hh`, `db_ih`, `db_hh`, `dh0`, `dc0`.
5. `clip_grad_norm(grads, max_norm)`: chuẩn L2 gộp mọi mảng; nếu lớn hơn `max_norm` thì nhân mọi mảng (tại chỗ) với
   `max_norm / (total + 1e-6)`. Trả chuẩn trước khi cắt.

## Tiêu chí đạt

- Khởi tạo đúng shape, khoảng, phân phối đều (cả bias), cùng seed cho cùng trọng số.
- `forward` khớp `nn.LSTM` (float64, cùng trọng số, có `h0`, `c0`) tới `1e-12`; input cỡ $$10^4$$ không tràn số.
- `backward` khớp autograd của `nn.LSTM` cho `x`, cả 4 tham số, `h0`, `c0` tới `1e-10`, kể cả khi loss phụ thuộc
  `h_T`, `c_T`; gọi hai lần cho cùng gradient.
- `clip_grad_norm` khớp `torch.nn.utils.clip_grad_norm_`.
- Đặt bias cổng quên bằng 3: gradient từ bước 50 về bước 1 còn lớn hơn $$10^{-4}$$ lần gradient ở bước cuối.

## Gợi ý

### Gợi ý 1

Mỗi bước lưu `(x_t, h_{t-1}, c_{t-1}, i, f, g, o, tanh(c_t))`. Đi ngược: gradient vào $$h_t$$ là `dout[t]` cộng gradient
chảy về từ bước sau; gradient vào $$c_t$$ là phần chảy về từ bước sau cộng phần đi qua $$h_t = o \odot \tanh(c_t)$$.
Từ đó suy gradient của 4 khối $$z$$ (nhân đạo hàm sigmoid $$\sigma(1-\sigma)$$ hoặc tanh $$1 - g^2$$), rồi `dW` cộng dồn
**qua các bước thời gian** trong một lần backward.

### Gợi ý 2

Viết đạo hàm cho **một bước** trước, giả sử đã biết gradient vào $$h_t$$ và vào $$c_t$$. Mỗi khối trong bốn khối của $$dz$$ là
tích của ba thứ: gradient đi vào ($$dc$$ hoặc $$dh$$), "đối tác" của cổng đó trong phương trình $$c_t$$ hoặc $$h_t$$, và đạo hàm
của hàm kích hoạt viết qua chính giá trị đã lưu. Rồi tự hỏi: gradient về $$h_{t-1}$$ đi qua ma trận nào, còn gradient về
$$c_{t-1}$$ đi qua phép nhân nào (không qua ma trận nào cả). Test báo `dc0` sai mà `dh0` đúng thường là thiếu một đường vào
$$c_t$$. Hai bias cộng vào cùng một chỗ trong $$z_t$$, nên gradient của chúng có quan hệ gì?
