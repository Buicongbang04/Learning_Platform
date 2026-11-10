# Lời giải: mixed precision trên CIFAR-10, tự viết dynamic loss scaling

## Cách làm

**`cast_report`.** Đưa về float64, giữ phần tử hữu hạn khác 0, ép sang `dtype` rồi về float64 để so. Underflow là
`cast == 0`, overflow là `isinf(cast)`, sai số tương đối lấy trung vị trên phần còn lại. So ở float64 để chính phép đo không
làm tròn thêm.

**`DynamicLossScaler`.** Trạng thái: `scale_value`, bộ đếm bước tốt, hai cờ của bước hiện tại (`unscaled`, `found_inf`).

- `scale(loss)`: `loss * scale_value`.
- `unscale_(optimizer)`: nếu bước này đã unscale thì thôi; không thì nhân mọi `p.grad` với `1/scale` tại chỗ, gom cờ
  "không hữu hạn" của từng tensor rồi `.item()` **một lần** (mỗi `.item()` là một lần CPU chờ GPU).
- `step(optimizer)`: gọi `unscale_` (không làm gì nếu đã gọi), có inf thì không `optimizer.step()`.
- `update()`: inf thì nhân `backoff_factor` và đếm lại; không thì đếm thêm, đủ `growth_interval` thì nhân `growth_factor`
  và đếm lại; xoá hai cờ.

Đối chiếu với `torch.amp.GradScaler("cpu", init_scale=8, growth_interval=3)` trên 9 bước, chèn inf ở bước 2 và 6: cả hai
cho chuỗi scale `8, 8, 4, 4, 4, 8, 4, 4, 4` (bước 5 là bước tốt thứ ba liên tiếp nên tăng lên 8) và cùng trọng số.

**`train_step`.** Thứ tự là toàn bộ bài:

1. Forward trong `torch.autocast(..., enabled=amp_dtype is not None)`; loss `F.cross_entropy(logits.float(), y)`.
2. `optimizer.zero_grad(set_to_none=True)`.
3. `scaler.scale(loss).backward()`.
4. `scaler.unscale_(optimizer)`, rồi `clip_grad_norm_` (trả norm trước khi clip; `inf` nếu không clip).
5. `scaler.step(optimizer)`, `scaler.update()`.

`stepped = isfinite(grad_norm)`: khi có inf/NaN, norm không hữu hạn và scaler đã bỏ bước. Một `GradScaler(enabled=False)`
cho fp32 và bf16 làm cùng một hàm chạy được mọi chế độ.

## Kết quả thật

**Ép kiểu** (`samples = [1e-9, 1e-7, 1e-5, 1 + 2^-12, 3.14159, 7e4, 1e6]`): fp16 underflow 1/7 (`1e-9`), overflow 2/7
(`7e4`, `1e6`); bf16 không mất phần tử nào nhưng sai số tương đối trung vị 1.2e-3 so với 3.1e-4 của fp16.

**Gradient thật**, ResNet-9 W=32 lúc khởi tạo (seed 0), 256 ảnh train đầu, fp32 trên CPU:

| Gradient theo | Số phần tử | Trung vị \|g\| | fp16 underflow ở scale 1 | ở $$2^8$$ | ở $$2^{16}$$ | bf16 underflow |
| --- | --- | --- | --- | --- | --- | --- |
| trọng số | 1 646 122 | 3.81e-03 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| activation (output 8 conv) | 48 234 496 | 2.13e-07 | **0.1208** | 0.0004 | 0.0000 | 0.0000 |

Gradient theo trọng số là tổng trên cả batch và cả không gian ảnh nên lớn; gradient theo activation thì mỗi phần tử chỉ
là phần của một ảnh trong loss trung bình, trung vị nhỏ hơn 18 000 lần. **12% trong số đó thành 0 ở fp16**, và đó chính là
thứ backward fp16 tính và truyền ngược qua từng conv. Nhân $$2^{16}$$ thì tỉ lệ underflow và tỉ lệ tràn đều làm tròn về 0.0000, và sai số tương đối trở về mức 1.7e-4 của fp16 bình thường.

**Train ResNet-9 W=32** trên CIFAR-10 đầy đủ, 3 epoch, batch 256, SGD Nesterov + OneCycle (peak 0.1), dữ liệu uint8 nằm
trên GPU, augmentation theo batch, `channels_last`; RTX 3050 Laptop 4GB:

| Cấu hình | s/epoch | Peak MiB | Test acc | Bước bị bỏ | Scale cuối | Loss 20 bước cuối |
| --- | --- | --- | --- | --- | --- | --- |
| fp32 (conv dùng TF32) | 18.6 | 664 | 0.8026 (lần chạy lại: 0.7874) | 0 | | 0.605 |
| fp16 + GradScaler | 13.9 | 460 | 0.7914 | 1 | 32 768 | 0.631 |
| bf16 | 14.4 | 460 | 0.7870 | 0 | | 0.639 |
| fp16 không scaler | 14.0 | 460 | 0.7975 | 0 | | 0.614 |
| fp16 + `DynamicLossScaler` | 16.3 | 460 | 0.7914 | 1 | 32 768 | 0.631 |

Đọc kết quả:

- **AMP nhanh hơn 1.3×** cả vòng train (18.6 so với 13.9 s/epoch), ít hơn mức 2× của riêng bước forward/backward ở bảng
  mục 4 lý thuyết: augmentation, chuẩn hoá, BatchNorm, optimizer, đánh giá không được lợi từ Tensor Core.
- **Peak memory giảm 31%** (664 xuống 460 MiB), không phải 50%: 150 MiB là chính tập train uint8 nằm trên GPU, tham số,
  gradient, momentum vẫn fp32, chỉ activation xuống 16 bit.
- **Accuracy ngang nhau**: mọi cấu hình nằm trong khoảng 0.787–0.803 sau 3 epoch; chênh lệch cỡ dao động giữa các lần chạy
  (kernel cuDNN không tất định: chạy lại cả notebook, fp32 ra 0.7874 thay vì 0.8026, các cấu hình 16 bit ra đúng số cũ), không
  phải hiệu ứng của dtype. Lần chạy lại đó GPU có tiến trình khác nên thời gian chậm 2–3 lần, nhưng peak memory giữ nguyên.
- GradScaler bỏ đúng **1 bước** (ở $$S = 2^{16}$$ gradient tràn) rồi ở $$2^{15}$$ suốt 584 bước còn lại (chưa đủ
  2 000 bước tốt để tăng lại). Scaler của bạn cho **cùng** accuracy và loss tới 3 chữ số: cùng phép toán, cùng quyết định bỏ
  bước. Nó chậm hơn 2.4 s/epoch vì mỗi tham số một phép `isfinite` riêng; `GradScaler` gộp việc này trong một kernel
  (`_amp_foreach_non_finite_check_and_unscale_`).
- **fp16 không scaler vẫn train được** ở đây: ResNet-9 có BatchNorm sau mỗi conv, và 12% activation gradient bị xoá là
  những phần tử nhỏ nhất, đóng góp ít vào gradient trọng số. Điều đó không làm loss scaling thừa: model sâu hơn, batch
  lớn hơn (gradient theo activation tỉ lệ $$1/B$$), loss có hệ số nhỏ (auxiliary loss nhân 0.01), hoặc Transformer không
  BatchNorm thì phần bị xoá lớn dần và model ngừng học mà không báo lỗi. Với bf16 thì câu hỏi biến mất.

Notebook chạy bằng env gốc (CPU, W=16, 10 000 ảnh, 2 epoch, chỉ fp32 và bf16) mất khoảng 3–7 phút tuỳ tải máy; accuracy
khoảng 0.35, và bf16 **chậm hơn** fp32 trên CPU không có lệnh AMX (1.6× ở phép đo một bước khi máy rảnh, tới 6× khi
máy đang bận): mixed precision là tối ưu cho phần cứng
có đơn vị 16 bit, không phải luôn nhanh hơn.

## Bẫy thường gặp

- Clip trước `unscale_`: ngưỡng clip nhỏ đi $$S$$ lần (test đặt $$S = 1024$$, `max_norm=0.5`: bước cập nhật dài 0.5/1024
  thay vì 0.5).
- `optimizer.step()` thay vì `scaler.step(optimizer)`: bước có inf vẫn được áp, trọng số thành NaN ngay.
- Tự viết scaler mà không đặt lại bộ đếm sau khi tăng scale: scale tăng mỗi bước sau lần tăng đầu (test `growth_interval=3`
  bắt được).
- Tính loss trong autocast bằng `log(softmax(...))` tự viết: softmax ở fp16 trên CPU, log của số nhỏ thành `-inf`. Dùng
  `F.cross_entropy` trên logits `.float()`.
- Đo thời gian GPU không `torch.cuda.synchronize()`: kernel chạy bất đồng bộ, đồng hồ dừng khi CPU xếp hàng xong chứ không
  phải khi GPU tính xong.
