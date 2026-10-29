# Lời giải: BatchNorm1d và dropout bằng numpy

## Cách làm

**BatchNorm1d, forward.** Khi train: `mean = x.mean(0)`, `var = x.var(0)` (chia $$N$$, dùng để chuẩn hoá), rồi
cập nhật running stats bằng trung bình trượt, với running var nhân thêm $$N/(N-1)$$ để thành phương sai không
lệch như PyTorch. Khi eval: lấy `running_mean`, `running_var` thay cho thống kê batch, không đổi chúng. Hai
chế độ dùng chung phần còn lại: $$\hat x = (x - \mu)/\sqrt{\sigma^2 + \epsilon}$$, $$y = \gamma\hat x + \beta$$. Cache $$\hat x$$,
$$1/\sqrt{\sigma^2 + \epsilon}$$ và chế độ.

Batch 1 mẫu khi train thì $$x - \mu = 0$$: output luôn bằng $$\beta$$, gradient về $$x$$ bằng 0, còn running var chia
cho $$N - 1 = 0$$. PyTorch báo lỗi ngay; ở đây cũng vậy (`ValueError`), thay vì để model âm thầm không học.

**BatchNorm1d, backward.** $$d\gamma = \sum_n g_n \hat x_n$$, $$d\beta = \sum_n g_n$$. Với gradient theo $$x$$, đặt $$\tilde g = \gamma \odot g$$:

$$
\frac{\partial L}{\partial x} = \frac{1}{N\sqrt{\sigma^2 + \epsilon}}\left(N\tilde g - \sum_n \tilde g_n - \hat x\sum_n \tilde g_n\hat x_n\right)
$$

Hai số hạng trừ là phần gradient chảy qua $$\mu$$ và $$\sigma^2$$, vì mọi mẫu trong batch cùng góp vào hai thống
kê đó. Hệ quả: tổng gradient theo $$x$$ trên mỗi cột bằng 0, và gradient vuông góc với $$\hat x$$. Khi eval,
$$\mu$$ và $$\sigma^2$$ là hằng số nên chỉ còn $$\tilde g/\sqrt{\sigma^2 + \epsilon}$$. Test gradient check cả hai chế độ.

**Dropout.** `mask = (rng.random(x.shape) >= p) / (1 - p)`, ép về dtype của `x`, lưu lại; forward trả
`x * mask`, backward trả `grad * mask`. Eval hoặc `p = 0`: đặt `mask = None` và trả nguyên input, backward
trả nguyên gradient. Chia $$1 - p$$ ngay trong mask là "inverted": kỳ vọng không đổi khi train, nên eval
không phải nhân gì.

## Kết quả thật

Đối chiếu PyTorch (float64, batch 16 × 4, mean 3, std 2): sai lệch lớn nhất 8.9e-16 khi train, 4.4e-16 khi
eval, running var trùng tới 4 chữ số in ra. Dropout $$p = 0.3$$ trên $$10^6$$ phần tử: mean 1.0000, tỉ lệ số 0
0.3000.

MLP 784-256-256-10 (He init, float32) trên **10 000** ảnh train đầu, 15 epoch, SGD lr 0.1, batch 64, seed 0,
`OMP_NUM_THREADS=4`, test trên 10 000 ảnh test:

| Cấu hình | Train loss epoch cuối | Train acc | Test acc epoch 1 | Test acc cuối | Thời gian |
| --- | --- | --- | --- | --- | --- |
| không BN, không dropout | 0.022 | 0.9983 | 0.8571 | 0.9514 | 1.8 s |
| BN, không dropout | 0.009 | 1.0000 | **0.9269** | 0.9582 | 2.9 s |
| không BN, dropout 0.3 | 0.087 | 0.9892 | 0.8859 | 0.9500 | 2.2 s |
| BN, dropout 0.3 | 0.087 | 0.9970 | 0.9192 | **0.9595** | 3.3 s |

Đánh giá model "BN, dropout 0.3" ở sai chế độ:

| Cách đánh giá | Test acc |
| --- | --- |
| eval mode | 0.9595 |
| train mode, batch 1000 | 0.9371 |
| train mode, batch 4 | 0.7499 |
| eval mode lại, sau hai lượt trên | 0.9546 |

Đọc kết quả:

- **BatchNorm tăng tốc rõ nhất ở đầu**: sau 1 epoch, 0.927 so với 0.857, và đường cong test của bản có BN
  ít dao động hơn. Sau 15 epoch khoảng cách thu lại còn dưới 1 điểm: trên MLP nhỏ, BN chủ yếu cho hội tụ
  nhanh và ổn định, không đổi trần accuracy. Lợi lớn hơn ở mạng sâu và khi muốn dùng lr lớn.
- **Dropout nới khoảng cách train/test**: train loss cuối tăng từ 0.022 lên 0.087 (đo khi dropout đang bật)
  và train acc giảm, nhưng test acc gần như không đổi. Với 10 000 ảnh và 15 epoch, MLP này chưa overfit tới
  mức test accuracy giảm, nên regularization chưa có nhiều để sửa. Dropout không vô dụng; nó cần đúng chỗ
  (model lớn so với dữ liệu, train lâu), và phải đo trên validation để biết.
- **Quên eval** tốn 2 điểm với batch 1000 (dropout bật, BN dùng thống kê batch), và 21 điểm với batch 4
  (thống kê từ 4 ảnh quá nhiễu). Tệ hơn, mỗi forward ở chế độ train **cập nhật running stats**: hai lượt đánh
  giá sai đã ghi đè thống kê học từ train bằng thống kê của các batch test cuối, nên chuyển lại eval vẫn mất
  0.5 điểm. Trong PyTorch, `torch.no_grad()` không ngăn điều này; chỉ `model.eval()` mới ngăn.

## Bẫy thường gặp

- Running var bằng `x.var(0)` (chia $$N$$): forward khi train vẫn đúng, chỉ eval lệch một chút. Test so với
  PyTorch ở `atol=1e-6` bắt được ngay.
- Backward BN bỏ hai số hạng qua $$\mu, \sigma^2$$ (coi chúng là hằng số như khi eval): gradient check khi train
  báo sai lớn.
- Dropout sinh mask mới trong backward, hoặc không nhân $$1/(1-p)$$ khi train rồi nhân $$1-p$$ khi eval (dropout
  "thường"): cách sau đúng về kỳ vọng nhưng làm eval phải biết $$p$$.
- Sửa tại chỗ (`x -= mean`) mảng input mà layer trước còn giữ trong cache: bug im lặng ở mục 7 lý thuyết.
