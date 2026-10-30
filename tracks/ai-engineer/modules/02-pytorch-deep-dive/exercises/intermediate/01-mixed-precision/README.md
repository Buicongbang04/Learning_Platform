---
title: Mixed precision trên CIFAR-10, tự viết dynamic loss scaling
level: intermediate
services: []
files:
  - path: starter/amp.ipynb
    note: 1 hàm đo, 1 lớp scaler, 1 hàm train_step TODO
  - path: tests/test_amp.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cifar10
  - uv run jupyter lab tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/intermediate/01-mixed-precision/starter/amp.ipynb
  - uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/intermediate/01-mixed-precision -q
---

## Mục tiêu

Hiểu mixed precision bằng số đo của chính bạn: gradient thật nằm ở đâu trên trục số fp16, loss scaling cứu được gì,
một bước train AMP phải theo thứ tự nào, và fp32, fp16, bf16 khác nhau bao nhiêu về tốc độ, bộ nhớ, accuracy trên
CIFAR-10. Làm xong bạn tự cài được `GradScaler` và biết khi nào không cần nó.

## Đề bài

**Phần cứng:** GPU 4GB · ~90 phút

Thời gian trên là thời gian làm bài. Chạy cả notebook bằng kernel `ai-gpu` mất khoảng 6 phút trên RTX 3050 (5 cấu hình ×
3 epoch); env gốc (CPU) chạy bản thu nhỏ trong 3–7 phút tuỳ máy, đủ để kiểm code nhưng không để đọc số.

Mở `starter/amp.ipynb` (mục 4 lý thuyết):

1. `cast_report(t, dtype)`: ép `t` về `dtype`, trên các phần tử hữu hạn khác 0 đo tỉ lệ underflow (thành 0), overflow
   (thành ±inf) và trung vị sai số tương đối của phần còn lại.
2. `DynamicLossScaler`: `scale`, `unscale_`, `step`, `update`, `get_scale` cùng giao diện và cùng hành vi với
   `torch.amp.GradScaler`: gặp inf/NaN thì bỏ bước và nhân `backoff_factor`, đủ `growth_interval` bước tốt liên tiếp thì
   nhân `growth_factor`; `unscale_` hai lần trong một bước không chia hai lần.
3. `train_step(model, x, y, optimizer, scaler, amp_dtype, max_norm)`: forward trong `torch.autocast`, loss fp32, xoá
   gradient, backward trên loss đã scale, `unscale_` rồi mới đo norm và clip, `step`, `update`; trả loss, norm và cờ
   `stepped`.

Rồi chạy các cell `explore`: so `DynamicLossScaler` với `GradScaler` trên một chuỗi có gradient inf, đo underflow của
gradient thật (theo trọng số và theo activation) ở scale $$1$$, $$2^8$$, $$2^{16}$$, và train ResNet-9 (W=32) 3 epoch với
fp32, fp16 + GradScaler, bf16, fp16 không scaler, fp16 + scaler của bạn. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `cast_report` chỉ đếm phần tử hữu hạn khác 0, đúng underflow/overflow của fp16, đúng sai số tương đối của bf16.
- `DynamicLossScaler` cho cùng chuỗi scale và cùng trọng số với `torch.amp.GradScaler` qua 9 bước, khi không có inf, có
  inf rải rác, và inf liên tiếp; mặc định $$S = 2^{16}$$; `unscale_` gọi hai lần không chia hai lần; `step` tự unscale và bỏ
  qua bước có NaN.
- `train_step` ở fp32 khớp một vòng train viết tay qua hai bước (gradient được xoá); forward chạy ở bf16 khi
  `amp_dtype=torch.bfloat16` mà tham số vẫn fp32; norm trả về là norm đã unscale, trước khi clip, và bước cập nhật có độ
  dài đúng `max_norm`; input có inf thì `stepped=False`, tham số không đổi, scale giảm một nửa (cả với scaler của bạn).

## Gợi ý

### Gợi ý 1

`unscale_` duyệt `optimizer.param_groups`, chia `p.grad` tại chỗ cho scale và ghi lại có phần tử không hữu hạn nào không.
Giữ hai cờ cho bước hiện tại: đã unscale chưa, có inf không; `update()` dùng cờ inf rồi xoá cả hai. Để khớp
`GradScaler`, bộ đếm bước tốt về 0 mỗi khi gặp inf **và** mỗi khi vừa tăng scale.

### Gợi ý 2

Trong `train_step`: `with torch.autocast(device_type=x.device.type, dtype=amp_dtype or torch.float32, enabled=amp_dtype is not None)`;
loss là `F.cross_entropy(logits.float(), y)`. `torch.nn.utils.clip_grad_norm_` trả norm **trước** khi clip; với
`max_norm=None` truyền `float("inf")` để chỉ đo. `stepped` là norm có hữu hạn hay không.
