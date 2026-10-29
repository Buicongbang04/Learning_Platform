---
title: BatchNorm1d và dropout bằng numpy, khớp PyTorch
level: intermediate
services: []
files:
  - path: starter/regularize.ipynb
    note: 2 lớp, 6 phương thức TODO
  - path: tests/test_regularize.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py mnist
  - uv run jupyter lab tracks/ai-engineer/modules/01-nn-from-scratch/exercises/intermediate/03-batchnorm-dropout/starter/regularize.ipynb
  - uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/intermediate/03-batchnorm-dropout -q
---

## Mục tiêu

Tự viết hai layer hành xử khác nhau giữa train và eval, BatchNorm1d và inverted dropout, khớp
`torch.nn.BatchNorm1d` tới từng con số kể cả running var. Ghép vào MLP trên MNIST để thấy chúng đổi đường
cong train thế nào, và thấy bằng số chuyện gì xảy ra khi quên chuyển sang eval.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Mở `starter/regularize.ipynb`. Cell đầu (tag `explore`) tải MNIST vào `data/raw/mnist` nếu chưa có.
Input của cả hai layer có shape `(N, D)`.

1. `BatchNorm1d(num_features, momentum=0.1, eps=1e-5)`, công thức ở mục 7 lý thuyết:
   - thuộc tính `gamma` (khởi tạo 1), `beta` (0), `running_mean` (0), `running_var` (1), shape `(D,)`;
   - `forward(x, training)`: khi train, chuẩn hoá bằng mean và phương sai **lệch** (chia $$N$$) của batch,
     cập nhật running stats bằng trung bình trượt, với running var dùng phương sai **không lệch** (chia
     $$N-1$$) như PyTorch; batch dưới 2 mẫu thì `ValueError`. Khi eval, dùng running stats và không đổi chúng;
   - `backward(grad)`: gán `dgamma`, `dbeta`, trả $$\partial L/\partial x$$ theo chế độ của lần forward trước.
2. `Dropout(p, rng)`: inverted dropout. Khi train, đặt 0 với xác suất $$p$$, phần còn lại nhân $$1/(1-p)$$, mask
   sinh mới mỗi lần forward từ `rng`; khi eval (hoặc `p = 0`) trả nguyên input. `backward` dùng đúng mask
   của forward. `p` ngoài $$[0, 1)$$ thì `ValueError`.

Rồi chạy các cell `explore`: đối chiếu với PyTorch, train MLP 784-256-256-10 trên 10 000 ảnh MNIST với
bốn cấu hình (có/không BatchNorm, có/không dropout 0.3), vẽ đường cong, và đánh giá thử ở sai chế độ. Cả
notebook chạy khoảng 15 giây. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- BatchNorm khởi tạo đúng; forward khi train (hai bước liên tiếp, momentum 0.1 và 0.3), running mean, running
  var và forward khi eval khớp `torch.nn.BatchNorm1d` với `atol=1e-6`; eval không đổi running stats, một mẫu
  riêng cho cùng kết quả như trong batch; batch 1 mẫu khi train báo `ValueError`.
- Gradient check `dx`, `dgamma`, `dbeta` đạt `rel < 1e-5` ở cả chế độ train và eval.
- Dropout `p = 0.3` trên $$10^6$$ phần tử: mean lệch 1 dưới 1%, tỉ lệ số 0 là 0.3 ± 0.01, phần khác 0 bằng
  $$1/0.7$$; eval và `p = 0` là phép đồng nhất; backward dùng lại đúng mask, forward sau sinh mask mới; cùng seed
  cho cùng mask.

## Gợi ý

### Gợi ý 1

Lưu vào cache những gì backward cần: $$\hat x$$, $$1/\sqrt{\sigma^2 + \epsilon}$$ và chế độ (train hay eval). numpy
`x.var(axis=0)` mặc định chia $$N$$; phương sai không lệch là nhân thêm $$N/(N-1)$$ (hoặc `ddof=1`). Khi eval,
$$\mu$$ và $$\sigma^2$$ là hằng số nên backward chỉ còn nhân $$\gamma/\sqrt{\sigma^2 + \epsilon}$$.

### Gợi ý 2

Backward khi train: đặt $$g = \gamma \odot \partial L/\partial y$$, rồi theo từng cột
$$\partial L/\partial x = \frac{1}{N\sqrt{\sigma^2 + \epsilon}}\left(N g - \sum_n g_n - \hat x \sum_n g_n \hat x_n\right)$$.
Mask dropout: so một mảng số đều `rng.random(x.shape)` với `p`, chia sẵn cho $$1-p$$ rồi lưu lại; backward
nhân `grad` với chính mảng đó, không gọi `rng` lần nữa.
