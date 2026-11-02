---
title: MLP bằng numpy trên MNIST thật
level: intermediate
services: []
files:
  - path: starter/mlp.ipynb
    note: 8 hàm/phương thức TODO
  - path: tests/test_mlp.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py mnist
  - uv run jupyter lab tracks/ai-engineer/modules/01-nn-from-scratch/exercises/intermediate/01-mlp-mnist/starter/mlp.ipynb
  - uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/intermediate/01-mlp-mnist -q
---

## Mục tiêu

Tự viết trọn vòng train của một MLP bằng numpy, từ đọc tệp idx gốc của MNIST tới SGD, và tái hiện
hai bảng SGD ở mục 6 phần lý thuyết. Làm xong bạn biết mỗi dòng của một vòng
train PyTorch thay cho đoạn numpy nào, và nhận ra ReLU chết khi lr quá lớn bằng số đo.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Mở `starter/mlp.ipynb`. Cell đầu (tag `explore`) tải MNIST vào `data/raw/mnist` nếu chưa có và đặt
`OMP_NUM_THREADS=4` trước khi import numpy (ma trận nhỏ, để BLAS dùng 16 luồng chậm hơn khoảng 5 lần).
Quy ước giống phần lý thuyết và bài Basic 03: batch theo dòng, `W` shape `(in, out)`, $$\text{out} = xW + b$$.

1. `load_mnist(root) -> (X_train, y_train, X_test, y_test)`: đọc 4 tệp idx gz bằng `gzip` + numpy (không
   dùng torchvision). Ảnh làm phẳng `(N, 784)`, `float32`, chia 255; nhãn `int64`.
2. `MLP(sizes, seed)`: `Linear → ReLU → … → Linear`, tầng cuối ra logits. `W` khởi tạo He (phân phối
   chuẩn, phương sai $$2/n_{in}$$), `b` bằng 0, đều `float32`; số ngẫu nhiên lấy lần lượt từ tầng đầu tới tầng
   cuối từ `np.random.default_rng(seed)`. Ba phương thức:
   - `forward(X)`: trả logits, lưu cache cho backward.
   - `loss_and_backward(X, y) -> float`: cross-entropy trung bình trên batch (log-softmax ổn định số),
     backward qua mọi tầng, lưu gradient.
   - `params()`: danh sách cặp `(tham số, gradient)` theo thứ tự `W1, b1, W2, b2, …`, là **chính các mảng**
     trong model (không phải bản sao).
3. `sgd_step(model, lr)`: $$\theta \leftarrow \theta - \eta\, g$$ tại chỗ cho mọi cặp trong `params()`.
4. `train_epoch(model, X, y, lr, batch_size, rng) -> float`: xáo bằng một hoán vị `rng.permutation(len(X))`
   cho cả `X` và `y`, đi hết dữ liệu theo minibatch, trả loss trung bình **theo mẫu** của epoch.
5. `accuracy(model, X, y) -> float`.

Rồi chạy các cell `explore`: kiểm loss ở bước 0 và overfit 32 ảnh, train 784-128-10 ba epoch với SGD lr
0.01 và 0.1, và thang lr 0.5 tới 5.0 đếm tỉ lệ ReLU chết. Cả notebook chạy khoảng 5 giây. Sau đó làm phần
trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `MLP([20, 16, 8, 4], 0).params()` có 6 cặp đúng shape, `float32`, bias bằng 0; std của `W` khớp He;
  cùng seed cho cùng trọng số, khác seed thì khác.
- Loss và gradient của mọi tham số khớp `torch.nn.functional.cross_entropy` + autograd cùng trọng số
  (`rtol=1e-4`).
- `sgd_step` sửa chính mảng trong model; `train_epoch` với `lr=0` trả đúng loss trên cả tập (trung bình
  theo mẫu, kể cả khi batch cuối ngắn hơn); loss epoch 2 nhỏ hơn epoch 1 trên dữ liệu sinh.
- Overfit 32 mẫu nhãn ngẫu nhiên tới accuracy 1.0 trong 200 bước SGD lr 0.5; cùng seed cho cùng kết quả.
- MNIST thật: `load_mnist` đúng shape, dtype, nhãn đầu tiên `[5, 0, 4, 1, 9]`; MLP `[784, 128, 10]`, lr 0.1,
  batch 64, 2 epoch trên 20 000 ảnh đầu đạt test accuracy ≥ 0.91 trong dưới 30 giây.
- Cell `explore` in ra bảng SGD ở mục 6 lý thuyết (lr 0.1: test acc 0.9636; máy khác có thể lệch ở chữ số thứ tư).

## Gợi ý

### Gợi ý 1

`np.frombuffer(data, dtype, count, offset)` đọc thẳng từ bytes, không cần vòng lặp. Dtype `">u4"` là số
nguyên không dấu 4 byte big-endian. Backward của MLP nhiều tầng là vòng lặp ngược qua các tầng, mỗi tầng
đúng ba dòng như hàm `forward_backward` ở mục 4 lý thuyết: `dW`, `db`, rồi gradient chảy về tầng trước.

### Gợi ý 2

Trong `sgd_step`, viết `p -= lr * g`, không viết `p = p - lr * g`: dòng sau tạo mảng mới và chỉ gán lại tên
cục bộ `p`, model không đổi gì, loss đứng yên mà không có lỗi nào. Trong `train_epoch`, cộng
`loss * len(batch)` rồi chia cho `len(X)`. Để khớp số trong bảng lý thuyết: `rng.normal(0, sqrt(2 / n_in),
(n_in, n_out))` rồi `.astype(np.float32)`, tầng đầu trước.
