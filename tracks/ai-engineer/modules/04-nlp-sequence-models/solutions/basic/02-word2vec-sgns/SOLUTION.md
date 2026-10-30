# Lời giải: word2vec SGNS bằng numpy

## Cách làm

**Vocab, subsampling, nhiễu.** `Counter` rồi `sorted(..., key=lambda w: (-freq[w], w))`: luật hoà cố định để id tái lập
được. `keep_probs` đúng công thức trong mã C gốc của word2vec, $$\min(1, (\sqrt{f/t} + 1)\, t/f)$$: từ có tần suất
$$f = t$$ được giữ với xác suất 1, từ có $$f = 100t$$ còn khoảng 11%. Phân phối nhiễu là `counts ** 0.75` chuẩn hoá.

**Bước SGD.** Với batch B cặp, K negative:

| Đại lượng | Shape | Công thức |
| --- | --- | --- |
| $$v$$, $$u_o$$, $$u_k$$ | (B, d), (B, d), (B, K, d) | lấy dòng của `W_in`, `W_out` |
| điểm dương, âm | (B,), (B, K) | `sum(v * u_o)`, `einsum("bkd,bd->bk")` |
| loss | số | $$-\frac1B\left(\sum \log\sigma(s^+) + \sum \log\sigma(-s^-)\right)$$ |
| $$g^+$$, $$g^-$$ | (B,), (B, K) | $$(\sigma(s^+) - 1)/B$$, $$\sigma(s^-)/B$$ |
| $$\partial L/\partial v$$ | (B, d) | $$g^+ u_o + \sum_k g^-_k u_k$$ |
| $$\partial L/\partial u_o$$, $$\partial L/\partial u_k$$ | (B, d), (B, K, d) | $$g^+ v$$, $$g^-_k v$$ |

Cập nhật bằng `np.add.at` cho cả ba nhóm chỉ số. Mọi gradient tính từ $$v$$, $$u$$ **trước** cập nhật: nếu cập nhật
`W_in` trước rồi mới lấy $$v$$ để tính gradient của `W_out` thì kết quả lệch nhẹ khỏi autograd.

`log σ(x)` viết bằng `-np.logaddexp(0, -x)`; `σ(x) = exp(log σ(x))` (có thể underflow về 0, đúng giá trị). Với điểm
-1800, cách ngây thơ `np.log(1 / (1 + np.exp(1800)))` tràn ra `inf` rồi `log(0) = -inf`.

**Láng giềng.** Chuẩn hoá mọi dòng về độ dài 1 rồi nhân ma trận. Tích vô hướng thô ưu tiên vector dài, mà độ dài vector
word2vec tương quan với tần suất từ, nên láng giềng toàn là từ phổ biến.

## Kết quả thật

- Khớp `torch.autograd` tới `1e-12` trên batch có chỉ số trùng.
- Toy hai chủ đề: 400 câu × 8 từ, window 2, 5 negative, lr 0.5, 3 epoch (0.4 giây): loss trung bình 50 batch đầu
  4.04, 50 batch cuối 2.11; 5 láng giềng của "phở" đúng 5 món ăn còn lại.
- Tốc độ bản numpy với V = 30 000, d = 100, batch 1 024, 5 negative: khoảng 21 000 cặp mỗi giây (CPU 4 luồng, máy đang
  chạy việc khác). Corpus Wikipedia của bài Intermediate 01 sinh khoảng 13 triệu cặp mỗi epoch, tức hơn 10 phút một epoch;
  bản tensor PyTorch cùng công thức (`nn.Embedding(sparse=True)` thay cho `np.add.at`) chạy một epoch trong khoảng 35 giây
  khi máy rảnh. Vì vậy bài Intermediate 01 chuyển phần tính sang PyTorch.

## Bẫy thường gặp

- `W[idx] -= ...` với chỉ số trùng: mất cập nhật, embedding học chậm, không lỗi nào báo. Test khớp autograd bắt được.
- Quên chia B ở gradient trong khi loss là trung bình: lr hiệu dụng nhân B lần.
- Dùng softmax đầy đủ "cho chắc": đúng nhưng $$O(Vd)$$ mỗi cặp, chậm hàng nghìn lần với vocab thật.
- Lấy mẫu âm theo tần suất thô (mũ 1): negative gần như toàn "của", "và", "là"; từ hiếm hiếm khi bị đẩy ra xa.
