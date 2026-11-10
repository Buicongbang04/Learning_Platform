# Lời giải: bộ nhớ khi train, gradient accumulation và activation checkpointing

## Cách làm

**`saved_tensor_bytes`.** Lấy trước tập `data_ptr` của storage mọi tham số. Pack hook nhận từng tensor autograd lưu lại, ghi
`saved[storage.data_ptr()] = storage.nbytes()` nếu không phải storage của tham số, và **trả lại chính tensor** (hook không được
đổi thứ backward nhận). Dict theo `data_ptr` tự gộp các view và các op lưu cùng một tensor (`ReLU` lưu output, `Linear` sau đó
lưu chính tensor đó làm input). Trong `no_grad` không op nào lưu gì nên kết quả là 0.

**`state_bytes`.** `numel() * element_size()` cho tham số, `.grad` khác `None`, và mọi tensor trong `optimizer.state` (với AdamW
là `exp_avg`, `exp_avg_sq` và `step`; `step` là một tensor vô hướng mỗi tham số).

**`accumulate_step`.** `zero_grad` một lần; với mỗi micro-batch, `loss = F.cross_entropy(model(xb), yb) * len(xb) / len(x)` rồi
`backward()`; `step` một lần; trả tổng các `loss.item()`. Trọng số `len(xb) / len(x)` làm tổng các gradient đúng bằng gradient của
loss trung bình trên cả batch (mục 5 lý thuyết). Chia cho số micro-batch sai khi micro-batch cuối nhỏ hơn: test batch 10, micro 4
(4 + 4 + 2) bắt được.

**`CheckpointedSequential`.** `self.layers = nn.ModuleList(layers)` nên `state_dict` có khoá `layers.<i>.*`. Chia chỉ số layer
thành các đoạn liên tiếp `ceil(n / segments)` phần tử. Forward: khi `self.training and torch.is_grad_enabled()`, mỗi đoạn chạy qua
`checkpoint(self._run, idx, x, use_reentrant=False)`, trong đó `_run` chạy lần lượt các layer của đoạn; ngược lại chạy thường.
`use_reentrant=False` lưu trạng thái RNG khi forward và khôi phục nó khi tính lại, nên Dropout ra đúng mask cũ và gradient khớp
bản thường tới từng bit (test so với `nn.Sequential` cùng seed).

## Kết quả thật

**Activation** (CPU, chỉ phụ thuộc shape nên giống nhau trên mọi máy), ResNet-9 W=32, batch 128 ảnh CIFAR-10:

| Cấu hình | Activation giữ cho backward |
| --- | --- |
| fp32 | 237.9 MiB |
| autocast bf16 | 136.2 MiB |
| `no_grad` | 0 |
| checkpoint 12 đoạn (mỗi layer cấp cao một đoạn) | 97.6 MiB |
| checkpoint 4 đoạn | 15.5 MiB |
| checkpoint 2 đoạn | 5.5 MiB |
| checkpoint 1 đoạn | 1.5 MiB (chỉ còn ảnh input) |

bf16 không giảm đúng một nửa (136.2 so với 119.0): input của BatchNorm và các phép tính fp32 trong autocast vẫn được lưu ở fp32,
và chỉ số của max-pool là int64.

**Trạng thái train** sau một bước (1 646 122 tham số): SGD 8.0 byte/tham số (tham số + gradient), SGD momentum 12.0, AdamW 16.0
(hai moment; `step` thêm vài chục byte cho cả model). Ở batch 128, activation fp32 (237.9 MiB) lớn gấp 9 lần trạng thái AdamW
(25.1 MiB): với CNN nhỏ, cần gạt hiệu quả là batch, AMP và checkpoint, không phải optimizer.

**Accumulation** 4 × 64 so với 256, cùng trọng số, sai lệch tương đối của gradient: BatchNorm **2.80e-01**, GroupNorm(8)
**8.44e-07** (sai số làm tròn float32). Với BatchNorm, accumulation là một model khác (thống kê trên 64 ảnh), không phải "batch 256
chia nhỏ".

**GPU** (RTX 3050 4GB, GPU có tiến trình khác lúc đo: bộ nhớ đáng tin, thời gian chỉ để so tương đối). Một bước ResNet-9 W=64,
batch 256, fp32, AdamW, `memory_allocated` so với lúc trước khi tạo model:

| Thời điểm | MiB |
| --- | --- |
| sau khi tạo model | 28 |
| sau forward | 982 |
| sau backward | 71 |
| sau `step` (AdamW tạo hai moment) | 121 |
| sau `zero_grad(set_to_none=True)`, bỏ `loss` | 95 |
| peak | 1 023 |

Đỉnh nằm **cuối forward**: activation chiếm gần 1 GB, backward giải phóng chúng dần. Trạng thái AdamW chỉ thêm 50 MiB.

Peak memory theo batch, checkpoint và dtype (W=64, SGD momentum):

| | không checkpoint | checkpoint 4 đoạn | checkpoint 1 đoạn |
| --- | --- | --- | --- |
| fp32 batch 64 | 341 MiB | 257 MiB | 332 MiB |
| fp32 batch 128 | 580 MiB | 419 MiB | 564 MiB |
| fp32 batch 256 | 1 054 MiB | 739 MiB | 1 043 MiB |
| bf16 batch 64 | 244 MiB | 182 MiB | 226 MiB |
| bf16 batch 128 | 377 MiB | 267 MiB | 357 MiB |
| bf16 batch 256 | 647 MiB | 437 MiB | 627 MiB |

- Checkpoint 4 đoạn giảm peak khoảng 30% (1 054 xuống 739 MiB ở fp32 batch 256); 1 đoạn gần như không giảm (1 043 MiB) vì lúc
  backward tính lại, toàn bộ activation lại nằm trong bộ nhớ cùng lúc. Bảng activation ở trên (1.5 MiB) chỉ đúng **giữa** forward
  và backward, không phải ở đỉnh.
- bf16 và checkpoint cộng dồn: bf16 + 4 đoạn ở batch 256 (437 MiB) nhỏ hơn fp32 không checkpoint ở batch 128 (580 MiB).
- Thời gian: checkpoint thêm một lần forward cho mỗi đoạn; trong lần đo trên GPU dùng chung, bước fp32 batch 256 từ 765 ms lên
  826 ms (4 đoạn) và 1 156 ms (1 đoạn). Đo lại khi GPU rảnh trước khi dùng con số tuyệt đối.

**Profiler** (3 bước, W=32, batch 128, fp32, model **không** `channels_last`): `convolution_backward` chiếm 56% thời gian CUDA,
các kernel `nchwToNhwcKernel` 8.6%: cuDNN dùng Tensor Core (TF32) ở layout NHWC và phải đổi layout qua lại vì model ở NCHW. Theo
bộ nhớ, `cudnn_convolution` (output conv) và `threshold_backward` cấp phát nhiều nhất. Trên CPU, profiler cho bảng tương tự với
`mkldnn_convolution` và `convolution_backward` đứng đầu.

## Bẫy thường gặp

- Pack hook không trả gì (`return None`): backward nhận `None` và lỗi. Unpack phải trả đúng tensor.
- Đếm theo `id(t)` hoặc `t.numel()` thay vì storage: đếm hai lần các view và các tensor được lưu chung (test hai view của `exp`).
- Bỏ qua storage của tham số bằng cách so `t is p`: `Linear` lưu `weight.t()`, một view khác đối tượng nhưng cùng storage.
- `checkpoint(..., use_reentrant=False, preserve_rng_state=False)`: Dropout tính lại sinh mask khác, gradient sai im lặng.
- Checkpoint cả khi eval hoặc trong `no_grad`: thừa (không có gì để lưu) và với bản reentrant còn cảnh báo.
- Đo bộ nhớ GPU bằng `nvidia-smi`: thấy cả cache của allocator, context CUDA và tiến trình khác.
