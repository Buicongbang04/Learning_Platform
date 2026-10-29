# Lời giải: vòng train có early stopping

## Cách làm

Vòng train chuẩn có bốn bước cho mỗi batch, và thứ tự là bắt buộc:

1. `optimizer.zero_grad()`: gradient trong PyTorch **cộng dồn** (như bản autograd tự viết ở bài
   Basic 01). Quên bước này thì mỗi step dùng tổng gradient của mọi batch trước đó.
2. Forward, tính loss.
3. `loss.backward()`: điền `.grad` cho mọi tham số.
4. `optimizer.step()`: cập nhật tham số từ `.grad` (và trạng thái riêng của optimizer như momentum).

`evaluate` bật `model.eval()` (dropout tắt, BatchNorm dùng running mean/var) và `torch.no_grad()`
(không dựng graph, tiết kiệm bộ nhớ và thời gian). Hai thứ này độc lập: `eval()` không tắt
gradient, `no_grad()` không tắt dropout. Thiếu một trong hai là bug, chỉ khác nhau về triệu chứng.

Loss trung bình theo mẫu: cộng `loss.item() * len(yb)` rồi chia tổng số mẫu. Với 50 mẫu và batch
16, trung bình của 4 batch cho batch cuối (2 mẫu) trọng số bằng batch 16 mẫu: lệch nhỏ nhưng đủ để
so sánh hai model trên hai cách chia batch khác nhau bị sai.

Early stopping lưu `copy.deepcopy(model.state_dict())` ở epoch tốt nhất và nạp lại khi kết thúc.
`state_dict()` không sao chép: nó trả tham chiếu tới tensor đang sống, nên không deepcopy thì
"bản tốt nhất" luôn trùng với trọng số cuối cùng.

## Vì sao test dùng nhãn ngẫu nhiên

24 điểm train với nhãn ngẫu nhiên, model 2 tầng 128 nơ-ron: model học thuộc được hết, train loss
giảm mãi nhưng val loss (trên dữ liệu có cấu trúc thật) tăng sau vài epoch. Đó là overfitting thuần
tuý, nên early stopping chắc chắn kích hoạt sớm và test kiểm được cả số epoch lẫn việc khôi phục.

## Bẫy thường gặp

- Gọi `model.train()` ở đầu `fit` một lần, nhưng `evaluate` chuyển sang `eval()` và không ai chuyển
  lại: từ epoch thứ hai dropout tắt khi train. Đặt `model.train()` **trong** `train_one_epoch`.
- Cộng dồn `total += loss` (tensor) thay vì `loss.item()`: rò bộ nhớ vì giữ graph của mọi batch.
- Chọn epoch tốt nhất theo **test** loss: test bị dùng để chọn model, không còn là ước lượng khách
  quan.
- Early stopping theo accuracy với tập validation nhỏ: accuracy nhảy bậc thang, hay "hoà" nên dừng
  quá sớm. Val loss mượt hơn; nếu metric kinh doanh khác loss thì theo dõi cả hai.
