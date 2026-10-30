# Hướng làm: gỡ lỗi vòng train PyTorch hỏng mà không báo lỗi

Bài không có code lời giải: bản sửa chỉ là 5 chỗ, giá trị nằm ở quy trình khoanh vùng và `BUGS.md`. Dưới đây là 5 bug,
triệu chứng đo được của **từng bug khi chỉ còn mình nó** (4 bug kia đã sửa), cách phát hiện và cách sửa. Số liệu: CPU,
torch 2.14.1, `OMP_NUM_THREADS=4`, `train(seed=0)` mặc định trên 10 000 ảnh train đầu, val 2 000 ảnh test đầu (máy đang tải
nặng nên thời gian chỉ để tham khảo; accuracy có thể lệch vài phần nghìn theo số luồng).

## Năm bug

| # | Bug | Ở đâu | Loss epoch 4 | Val acc epoch 4 |
| --- | --- | --- | --- | --- |
| | Đã sửa cả 5 | | 1.155 | **0.596** |
| | Đủ 5 bug (notebook gốc) | | 2.228 | 0.224 |
| 1 | `reshape` thay `permute` | `preprocess` | 1.667 | 0.401 |
| 2 | `ResBlock` trong list Python | `Net.__init__` | 1.707 | 0.384 |
| 3 | softmax trước `cross_entropy` | `loss_fn` | 2.005 | 0.492 |
| 4 | `evaluate` không trả về train mode | `evaluate` (và `train` không gọi `model.train()`) | 1.830 | 0.328 |
| 5 | `zero_grad` trong vòng accumulation | `train_step` | 1.384 | 0.526 |

Mỗi dòng 1–5 là bản đã sửa cộng đúng một bug. Bản đã sửa đạt 0.596 sau 4 epoch trên 10 000 ảnh (một ResNet 78 042 tham số,
4 epoch trên CPU: đây là mức trần của thiết lập, không phải của CIFAR-10). Trên dữ liệu tổng hợp của test (1 024 ảnh, 3 epoch,
w = 8), bản sửa đạt 1.000; từng bug một mình cho 0.574 (bug 1), 0.590 (bug 2), 0.563 (bug 3), 0.258 (bug 4), 1.000 (bug 5,
chỉ test so gradient bắt được), đủ 5 bug 0.102.

### Bug 1: `reshape` thay vì `permute` khi đổi layout ảnh

- **Ở đâu.** `preprocess`: `images.reshape(n, c, h, w)` trên tensor `(N, H, W, C)`.
- **Triệu chứng.** Không lỗi, shape đúng `(N, 3, 32, 32)`, model vẫn học được một phần (pixel bị trộn theo một hoán vị
  cố định, nên vẫn còn chút cấu trúc màu); val acc 0.401 so với 0.596.
- **Phát hiện.** Vẽ lại một ảnh sau `preprocess` (đảo chuẩn hoá): thấy sọc nhiễu thay vì con vật. Hoặc so một pixel:
  `preprocess(x)[0, :, 0, 0]` phải bằng `(x[0, 0, 0] / 255 - MEAN) / STD`; bản lỗi cho kênh 0 là ba giá trị của ba
  kênh đầu tiên (mục 7 lý thuyết).
- **Sửa.** `images.permute(0, 3, 1, 2).float() / 255`.

### Bug 2: các `ResBlock` nằm trong list Python

- **Ở đâu.** `Net.__init__`: `self.blocks = [ResBlock(...), ...]`.
- **Triệu chứng.** Forward chạy, nhưng optimizer chỉ thấy **1 114** tham số (stem và head) thay vì 78 042; ba block giữ
  nguyên trọng số ngẫu nhiên, BatchNorm trong block không đổi chế độ khi `eval()`, `state_dict` thiếu mọi khoá `blocks.*`.
  Trên GPU bug này lộ ngay (`Expected all tensors to be on the same device`), trên CPU thì im lặng.
- **Phát hiện.** Notebook in sẵn số tham số sau khi train; tính tay: stem 464, ba block 4 672 + 14 528 + 57 728, head 650.
  Hoặc nạp `state_dict` vào một `Net` mới rồi so output; hoặc so trọng số `blocks[0].conv1` trước và sau một bước.
- **Sửa.** `nn.ModuleList([...])`.

### Bug 3: softmax trước `cross_entropy`

- **Ở đâu.** `loss_fn`: `F.cross_entropy(F.softmax(logits, 1), y)`.
- **Triệu chứng.** Loss bắt đầu gần 2.30 nhưng giảm rất chậm và có **sàn 1.46** với 10 lớp (mục 7 lý thuyết); gradient theo
  logits nhỏ đi khoảng 10 lần lúc khởi tạo.
- **Phát hiện.** Đưa vào `loss_fn` logits rất tự tin và đúng: loss phải về gần 0, bản lỗi ra 1.4612. Đọc tài liệu:
  `cross_entropy` nhận **logits** và tự làm `log_softmax`.
- **Sửa.** `return F.cross_entropy(logits, y)`.

### Bug 4: `evaluate` để model ở eval mode

- **Ở đâu.** `evaluate` gọi `model.eval()` và không trả lại; `train` gọi `evaluate` **trước** epoch đầu ("val acc trước khi
  train") và không tự gọi `model.train()`.
- **Triệu chứng.** Toàn bộ quá trình train chạy ở eval mode: BatchNorm chuẩn hoá bằng running stats khởi tạo (mean 0, var
  1) và không bao giờ cập nhật chúng, nên mạng gần như không có normalization; loss giảm chậm, val acc thấp.
- **Phát hiện.** `assert model.training` trong `train_step`; hoặc sau train, `model.stem[1].running_var` vẫn toàn số 1.
- **Sửa.** Trong `evaluate`, nhớ `was_training = model.training` rồi `model.train(was_training)` trước khi trả về (hoặc gọi
  `model.train()` đầu mỗi epoch; nên làm cả hai).

### Bug 5: `zero_grad` bên trong vòng accumulation

- **Ở đâu.** `train_step`: `optimizer.zero_grad()` nằm trong vòng lặp micro-batch.
- **Triệu chứng.** Gradient của micro-batch đầu bị xoá trước khi `step`: chỉ micro-batch cuối (64 ảnh) đóng góp, lại bị chia
  cho `accum_steps`, nên lr hiệu dụng bằng một nửa và gradient nhiễu gấp đôi. Model vẫn học, chỉ kém hơn: bug khó thấy nhất.
- **Phát hiện.** Với lr = 0, so gradient sau `train_step(accum_steps=2)` với gradient của một backward trên cả batch: lệch
  hẳn, đúng bằng một nửa gradient của micro-batch cuối.
- **Sửa.** Một `optimizer.zero_grad()` trước vòng lặp.

## Bug che nhau

- Với đủ 5 bug, loss đứng quanh 2.23–2.30 suốt 4 epoch: softmax hai lần (bug 3) tạo sàn loss và làm gradient nhỏ 10 lần, nên
  mọi bug khác đều "trông như" model không học. Sửa bug 3 trước để loss trở lại có ý nghĩa, rồi mới đọc được các triệu chứng khác.
- Bug 2 và bug 4 cùng làm BatchNorm không hoạt động như ý (block nằm ngoài model; hoặc cả model ở eval mode) nên dễ nhầm với
  nhau: phân biệt bằng số tham số trong optimizer (1 114) và bằng running stats (toàn 1).
- Bug 5 chỉ làm mất khoảng 7 điểm và test "train học được dữ liệu dễ" vẫn qua: không có phép so gradient với cả batch thì gần
  như chắc chắn lọt. Đây là lý do mọi "tối ưu" (accumulation, AMP, checkpoint) phải được so với một cài đặt tham chiếu.
- Bug 1 không làm hỏng loss hay gradient, chỉ làm dữ liệu vô nghĩa một phần: không phép thử nào trên model bắt được, phải nhìn
  dữ liệu.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 20 | Mọi test pass mà không đổi siêu tham số, kiến trúc dự định hay `DEVICE` |
| Đủ 5 bug, sửa ở gốc | 20 | Mỗi bug sửa đúng chỗ gây ra nó; không tăng lr, thêm epoch, bỏ accumulation hay bỏ BatchNorm để bù |
| Bằng chứng đo được | 25 | Mỗi bug có con số: số tham số 1 114 so với 78 042, sàn loss 1.46, running var toàn 1, gradient lệch so với cả batch, ảnh vẽ lại |
| Quy trình khoanh vùng | 20 | Tách tầng dữ liệu, model, loss/gradient, trạng thái giữa các bước; nêu bug nào che bug nào và thứ tự gỡ, val acc sau mỗi lần sửa |
| Bài học dùng lại được | 15 | Checklist trước khi train lâu, áp dụng cho dự án thật (assert shape và `model.training`, đếm tham số, overfit một batch, so với cài đặt tham chiếu) |

Đạt từ 70 điểm. `BUGS.md` chỉ liệt kê dòng đã sửa mà không có triệu chứng và phép thử không quá 40 điểm.
