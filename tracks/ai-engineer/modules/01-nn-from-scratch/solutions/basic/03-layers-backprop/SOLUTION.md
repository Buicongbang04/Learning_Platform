# Lời giải: Linear, ReLU, SoftmaxCrossEntropy có forward/backward

## Cách làm

Mỗi layer giữ hai hợp đồng: `forward` **lưu cache** những gì backward cần, `backward(grad)` nhận
$$\partial L/\partial\,\text{output}$$ và trả $$\partial L/\partial\,\text{input}$$ (nhân gradient đến với đạo hàm cục bộ).
Nhờ vậy layer ghép nối tiếp được mà không cần biết layer khác làm gì; backward chỉ việc gọi theo thứ
tự ngược với forward.

| Layer | Cache | Backward |
| --- | --- | --- |
| `Linear` | `x` | $$dW = x^\top g$$, $$db = \sum_n g_n$$, trả $$g W^\top$$ |
| `ReLU` | mặt nạ `x > 0` | trả $$g \odot \mathbb{1}[x > 0]$$ |
| `SoftmaxCrossEntropy` | `probs`, `y` | trả $$(p - \text{onehot}(y)) / N$$ |

**`Linear`.** Shape quyết định công thức: `dW` phải là `(in, out)`, chỉ `x.T @ grad` ra shape đó; `dx`
phải là `(N, in)`, chỉ `grad @ W.T`. `b` được broadcast cho N dòng khi forward nên backward cộng theo
trục batch. `dW`, `db` được **gán**, không cộng dồn: mỗi bước train một lần backward. PyTorch thì cộng
dồn vào `.grad` (để hỗ trợ gradient accumulation) và bắt bạn gọi `zero_grad()`; ở đây không có tham số
nào được dùng hai lần nên gán là đủ và tránh được lỗi quên xoá. Khởi tạo He:
`rng.normal(0, sqrt(2 / in_features), (in, out))`, chỉ lấy ngẫu nhiên từ `rng` truyền vào để tái lập.

**`ReLU`.** Lưu mặt nạ thay vì `x`: backward chỉ cần biết chỗ nào cho gradient qua. Mặt nạ `x > 0`
(nghiêm ngặt) cho đạo hàm 0 tại đúng 0, theo quy ước.

**`SoftmaxCrossEntropy`.** Gộp softmax và cross-entropy làm một layer vì hai lý do ở mục 2, 3 lý thuyết:
gradient theo logits rút gọn thành $$p - y$$ (không dựng Jacobian $$C \times C$$ của softmax), và log-xác suất
tính trực tiếp bằng log-softmax (trừ max từng dòng rồi log-sum-exp) nên không bao giờ `log(0)`.
Với logits `[[1000, 0]]` và nhãn 1: $$z - \max = [0, -1000]$$, log-sum-exp $$= \log(1 + e^{-1000}) = 0$$, log-xác
suất lớp 1 là $$-1000$$, loss đúng bằng 1000. Bản `np.log(softmax(z))` sẽ cho `inf`. `backward` copy
`probs` trước khi trừ 1 để gọi `backward` lần hai vẫn đúng.

## Kiểm bằng gì

Test dùng đúng chiến lược của mục 4: kiểm **từng layer riêng** với loss giả $$L = \sum(\text{out} \odot G)$$
(gradient đến chính là $$G$$), rồi kiểm cả chuỗi, rồi đối chiếu PyTorch cùng trọng số. Input của ReLU được
sinh với $$|x| \ge 0.1$$ để sai phân $$\pm 10^{-6}$$ không nhảy qua điểm gãy. Chuỗi MLP nhỏ (8 mẫu, 5-6-3)
cho rel cỡ 1e-10.

## Liên hệ với PyTorch

| Bản tự viết | PyTorch |
| --- | --- |
| `Linear.W` shape `(in, out)`, `x @ W` | `nn.Linear.weight` shape `(out, in)`, `x @ W.T` |
| He: `normal(0, sqrt(2/in))` | `nn.init.kaiming_normal_(w, nonlinearity="relu")`; mặc định của `nn.Linear` nhỏ hơn 6 lần về phương sai |
| `dW` gán mỗi backward | `.grad` cộng dồn, cần `optimizer.zero_grad()` |
| `SoftmaxCrossEntropy` | `nn.CrossEntropyLoss` (nhận logits, `reduction="mean"`) |
| cache trong layer | autograd lưu tensor cần cho backward trong `grad_fn` |

## Bẫy thường gặp

- Quên chia N trong `backward` của loss: loss vẫn giảm (như lr lớn gấp N) nhưng gradient check báo
  rel $$\frac{N-1}{N+1}$$.
- `np.maximum(x, 0)` trong forward nhưng mặt nạ `x >= 0` trong backward: lệch quy ước tại 0.
- Sửa `self.probs` tại chỗ trong `backward`: lần gọi thứ hai trừ 1 thêm lần nữa.
- Khởi tạo bằng `np.random.randn` toàn cục: chạy được nhưng không tái lập theo `rng`, và std 1 thay vì
  $$\sqrt{2/n_{in}}$$ (mục 5: mạng sâu nổ hoặc tắt).
