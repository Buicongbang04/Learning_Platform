# Lời giải: scaling laws trên GPT mini và quy tắc Chinchilla

## Các hàm

- `gpt_params`: mỗi Block của bài Basic 01 có hai LayerNorm ($$4d$$), `qkv` ($$3d^2 + 3d$$), `proj` ($$d^2 + d$$), `fc`
  ($$4d^2 + 4d$$), `proj` của MLP ($$4d^2 + d$$): tổng $$12d^2 + 13d$$. Non-embedding $$= L(12d^2 + 13d) + 2d$$ (thêm `ln_f`);
  total cộng $$Vd + T_{max}d$$, `lm_head` không cộng vì dùng chung với `tok_emb`. GPT-2 small (12 tầng, 768, vocab 50 257,
  context 1 024) ra 124 439 808, khớp con số "124M" của OpenAI.
- `train_flops`: $$6ND$$. Forward của một phép nhân ma trận $$d_{in} \times d_{out}$$ cho một token là $$2 d_{in} d_{out}$$ FLOP
  (nhân và cộng), tức $$2N$$ cho cả model; backward tính gradient theo cả input và trọng số, gấp đôi forward. Công thức bỏ qua phép
  nhân $$QK^\top$$ và $$AV$$ của attention (khoảng $$6 L T d$$ FLOP mỗi token khi train): nhỏ khi context $$T$$ nhỏ hơn nhiều so với
  $$12d$$, đáng kể khi context dài.
- `fit_power_law`: với $$c$$ cố định, khớp đường thẳng $$\log(y - c) = \log a - \alpha \log x$$ bằng `np.polyfit`; dò $$c$$ trên lưới
  2 000 điểm trong $$[0, \min y)$$, giữ $$c$$ có tổng bình phương sai số **trên $$y$$** nhỏ nhất. Chấm trên $$y$$ gốc vì
  đó là đại lượng cần khớp; sai số trong không gian $$\log(y - c)$$ của các $$c$$ khác nhau không cùng thang đo nên không so được.
  `scipy.optimize.curve_fit` cũng được, nhưng cần điểm khởi đầu tốt.
- `chinchilla_loss`: công thức với hằng số đã công bố. `chinchilla_optimal`: thay $$D = rN$$ vào $$C = 6ND$$:
  $$N = \sqrt{C / (6r)}$$, $$D = rN$$.

## Kết quả của notebook lời giải

«I03_SOL»

## Bẫy thường gặp

- Đếm cả `lm_head` khi đã tie: thừa $$Vd$$ tham số (với GPT-2 small là 38.6 triệu).
- So model khác kích thước nhưng cho model lớn learning rate quá cao: model lớn phân kỳ hoặc kém, đường cong scaling bị bẻ
  cong giả. Notebook dùng lr 2e-3 cho $$d \le 128$$, 1e-3 cho lớn hơn; đúng ra phải dò lr cho từng kích thước (muP giải quyết
  việc này bằng cách tham số hoá để lr chuyển được giữa các kích thước).
- Khớp power law có $$c$$ tự do từ 5 điểm: $$c$$ và $$\alpha$$ bù trừ nhau, nhiều cặp khớp gần như nhau. Báo cáo kèm khoảng dao
  động, đừng báo ba chữ số có nghĩa.
- Đọc $$6ND$$ là thời gian: thời gian thật còn phụ thuộc hiệu suất phần cứng (FLOP/s thực đạt thường 30-50% đỉnh ở model lớn, thấp
  hơn nhiều ở model tí hon vì chi phí khởi chạy kernel).
