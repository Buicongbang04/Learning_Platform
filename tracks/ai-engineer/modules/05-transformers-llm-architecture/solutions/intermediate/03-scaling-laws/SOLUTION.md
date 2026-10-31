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

Cùng 1 000 bài train và BPE 8 000 của bài Intermediate 01, 4 tầng, 4 head, chỉ đổi `n_embd`, seed 0.

| Bản | `n_embd` | $$N$$ non-embedding | Val loss | Khớp $$L(N)$$ |
| --- | --- | --- | --- | --- |
| CPU 4 luồng, 600 bước, batch 32 × 64 (1.23 triệu token mỗi model), cả notebook 8 phút | 32 / 64 / 96 / 128 / 192 | 50 880 / 200 064 / 447 552 / 793 344 / 1 779 840 | 6.460 / 6.116 / 6.041 / 5.795 / 5.679 | $$0.00 + 9.6\,N^{-0.036}$$ |
| kernel `ai-gpu`, PC RTX 3060, 2 000 bước, batch 32 × 128 (8.19 triệu token mỗi model), cả notebook 10 phút | 64 / 128 / 192 / 256 / 384 | 200 064 / 793 344 / 1 779 840 / 3 159 552 / 7 098 624 | 5.143 / 4.842 / 4.799 / 4.666 / 4.518 | $$0.34 + 7.6\,N^{-0.038}$$ |

Token mỗi tham số của model lớn nhất: 0.69 (CPU) và 1.15 (GPU), thấp xa mức 20 của Chinchilla; model nhỏ nhất thấy 24 (CPU) và
41 (GPU) token mỗi tham số.

Đọc kết quả:

- Loss giảm gần như thẳng theo $$\log N$$, có nhiễu (bản GPU: 128 và 192 gần bằng nhau; bản CPU: 64 và 96 gần bằng nhau). Không
  thấy đi ngang, nên $$c$$ không xác định được: bản CPU cho $$c = 0$$ (biên dưới của lưới), bản GPU cho 0.34. Hai số mũ
  0.036 và 0.038 gần nhau nhưng đều nhỏ hơn 0.076 của Kaplan, vì mọi model bị giới hạn bởi số token cố định.
- Biểu đồ loss theo compute: ở cùng mức compute, model nhỏ có loss train thấp hơn; các đường không cắt nhau trong ngân sách này.
  Model lớn chỉ thắng vì tiêu nhiều compute hơn. Đây là phía compute nhỏ của đường bao Chinchilla.
- Chinchilla: compute của Gopher $$6 \cdot 280 \cdot 10^9 \cdot 300 \cdot 10^9 = 5.04 \times 10^{23}$$ FLOP; quy tắc 20 token mỗi
  tham số khuyên 65 tỉ tham số và 1.30 nghìn tỉ token. Công thức loss cho Gopher 1.993, Chinchilla 1.937.
- Mutant đổi tiêu chí chọn $$c$$ sang sai số trong không gian $$\log(y - c)$$ vẫn qua test (trên dữ liệu test hai tiêu chí chọn
  gần cùng $$c$$); đây là lỗi về phương pháp, giải thích ở mục `fit_power_law` phía trên.

## Bẫy thường gặp

- Đếm cả `lm_head` khi đã tie: thừa $$Vd$$ tham số (với GPT-2 small là 38.6 triệu).
- So model khác kích thước nhưng cho model lớn learning rate quá cao: model lớn phân kỳ hoặc kém, đường cong scaling bị bẻ
  cong giả. Notebook dùng lr 2e-3 cho $$d \le 128$$, 1e-3 cho lớn hơn; đúng ra phải dò lr cho từng kích thước (muP giải quyết
  việc này bằng cách tham số hoá để lr chuyển được giữa các kích thước).
- Khớp power law có $$c$$ tự do từ 5 điểm: $$c$$ và $$\alpha$$ bù trừ nhau, nhiều cặp khớp gần như nhau. Báo cáo kèm khoảng dao
  động, đừng báo ba chữ số có nghĩa.
- Đọc $$6ND$$ là thời gian: thời gian thật còn phụ thuộc hiệu suất phần cứng (FLOP/s thực đạt thường 30-50% đỉnh ở model lớn, thấp
  hơn nhiều ở model tí hon vì chi phí khởi chạy kernel).
