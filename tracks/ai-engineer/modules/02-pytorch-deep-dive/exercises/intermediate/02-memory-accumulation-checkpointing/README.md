---
title: Bộ nhớ khi train, gradient accumulation và activation checkpointing
level: intermediate
services: []
files:
  - path: starter/memory.ipynb
    note: 3 hàm, 1 lớp TODO
  - path: tests/test_memory.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cifar10
  - uv run jupyter lab tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/intermediate/02-memory-accumulation-checkpointing/starter/memory.ipynb
  - uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/intermediate/02-memory-accumulation-checkpointing -q
---

## Mục tiêu

Trả lời câu hỏi đầu tiên khi gặp OOM: bộ nhớ đang nằm ở đâu. Bạn tự viết công cụ đo activation mà autograd giữ lại, đếm
trạng thái train thật, cài gradient accumulation và activation checkpointing đúng (kể cả với batch không chia hết và
Dropout), rồi đo trên ResNet-9 + CIFAR-10 bằng `torch.cuda`, `torch.profiler` và memory snapshot.

## Đề bài

**Phần cứng:** GPU 4GB · ~90 phút

Thời gian trên là thời gian làm bài. Phần đo activation, trạng thái train và accumulation chạy trên CPU trong khoảng 20 giây;
các cell **(GPU)** cần kernel `ai-gpu` (khoảng 2 phút trên RTX 3050), với env gốc chúng chỉ in lời nhắc.

Mở `starter/memory.ipynb` (mục 5 lý thuyết):

1. `saved_tensor_bytes(model, x)`: chạy `model(x)` trong `torch.autograd.graph.saved_tensors_hooks` và cộng byte của
   mọi storage được lưu cho backward, mỗi storage một lần, bỏ qua storage của tham số.
2. `state_bytes(model, optimizer)`: byte thật của tham số, gradient, và mọi tensor trong `optimizer.state`.
3. `accumulate_step(model, x, y, optimizer, micro_batch)`: một bước optimizer cho cả batch, forward/backward theo
   micro-batch, gradient bằng gradient của cross-entropy trung bình trên cả batch kể cả khi micro-batch cuối nhỏ hơn.
4. `CheckpointedSequential(layers, segments)`: như `nn.Sequential` nhưng mỗi đoạn liên tiếp chạy qua
   `torch.utils.checkpoint.checkpoint(..., use_reentrant=False)` khi train; output và gradient giống hệt bản thường,
   kể cả có Dropout.

Rồi chạy các cell `explore`: activation của ResNet-9 ở fp32, bf16, `no_grad` và với 12, 4, 2, 1 đoạn checkpoint; trạng
thái train với SGD, SGD momentum, AdamW; chênh lệch gradient giữa 4 × 64 và 256 với BatchNorm và GroupNorm; trên GPU, bộ
nhớ theo từng giai đoạn của một bước, peak memory và thời gian theo batch size × checkpoint × dtype, bảng profiler và
memory snapshot. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `saved_tensor_bytes` đúng trên MLP (input và output ReLU, không tính trọng số), đếm hai view của một storage một lần,
  trả 0 trong `no_grad`.
- `state_bytes` đúng với SGD (optimizer 0 byte), SGD momentum (bằng tham số), AdamW (khớp mọi tensor trong state);
  gradient 0 byte sau `zero_grad(set_to_none=True)`.
- `accumulate_step` khớp gradient, tham số (SGD momentum, hai bước liên tiếp) và loss của một backward trên cả batch, với
  micro-batch 4, 3, 10, 1 trên batch 10; `optimizer.step` chạy đúng một lần.
- `CheckpointedSequential`: `state_dict` như `nn.Sequential` có tiền tố `layers.`; output và gradient bằng bản thường
  với 1 tới 6 đoạn, có Dropout; byte được lưu đúng bằng input của các đoạn; eval và `no_grad` không checkpoint.

## Gợi ý

### Gợi ý 1

Trong pack hook, `t.untyped_storage().data_ptr()` định danh storage, `nbytes()` là kích thước của nó; tập `data_ptr` của
tham số lấy trước khi chạy. Pack hook phải trả lại chính tensor (`return t`) để backward dùng; unpack là
`lambda t: t`. Accumulation: nhân loss của micro-batch với `len(xb) / len(x)` rồi `backward()`.

### Gợi ý 2

Checkpoint cả một đoạn bằng một hàm chạy lần lượt các layer trong đoạn: `checkpoint(fn, *args, use_reentrant=False)`
nhận thêm tham số không phải tensor (vd. danh sách chỉ số layer). Chỉ checkpoint khi `self.training and torch.is_grad_enabled()`.
`use_reentrant=False` mặc định giữ trạng thái RNG, nên Dropout tính lại ra đúng mask cũ.
