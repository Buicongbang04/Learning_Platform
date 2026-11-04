---
title: Đo bộ nhớ theo rank - DDP và FSDP trên CPU
level: intermediate
services: []
files:
  - path: starter/shard_report.py
    note: 3 hàm TODO (wrap, local_numel, optimizer_tensors)
  - path: tests/test_shard.py
    note: Không sửa
run:
  - uv run python -m torch.distributed.run --nproc_per_node=2 --rdzv-backend=c10d --rdzv-endpoint=127.0.0.1:0 --local-addr=127.0.0.1 tracks/mlops/modules/15-distributed-training/exercises/intermediate/01-fsdp-shard-per-rank/starter/shard_report.py --out /tmp/mlops-15/shard
  - uv run pytest tracks/mlops/modules/15-distributed-training/exercises/intermediate/01-fsdp-shard-per-rank -q
---

## Mục tiêu

Thấy bằng số điều mục 3 của module nói bằng công thức: DDP giữ nguyên bản tham số, gradient và optimizer state trên **mỗi** rank, còn
FSDP (ZeRO-3) chia đều chúng cho các rank mà vẫn huấn luyện ra đúng cùng một model. Học cách đo đúng phần bộ nhớ thật sự nằm trên một
rank khi tham số là `DTensor`.

## Đề bài

`starter/shard_report.py` huấn luyện cùng một MLP (khoảng 148 nghìn tham số) hai lần trong một job torchrun hai tiến trình: lần đầu
bọc DDP, lần sau shard bằng FSDP2. Mỗi lần, mỗi rank dùng đúng cùng batch và cùng khởi tạo, Adam `STEPS` bước, rồi ghi
`<out>/<strategy>-rank<r>.json` gồm `losses` (từng bước), `param_numel`, `grad_numel`, `optimizer_numel`, `param_types`,
`model_state_bytes` (4 byte mỗi phần tử fp32 của ba phần trên). Điền 3 hàm:

- `wrap(model, strategy)`: `"ddp"` thì bọc `DistributedDataParallel`; `"fsdp"` thì gọi `fully_shard` (từ `torch.distributed.fsdp`) cho
  từng `nn.Linear` rồi cho cả model, trả model; strategy khác thì `ValueError`.
- `local_numel(tensors)`: tổng số phần tử mà **rank này giữ trong bộ nhớ**, cộng trên mọi tensor trong iterable, bỏ qua `None`.
- `optimizer_tensors(optimizer)`: mọi tensor trạng thái của optimizer có ít nhất 1 chiều (với Adam là `exp_avg`, `exp_avg_sq` của mỗi
  tham số; bỏ bộ đếm `step` 0 chiều).

Luật mà test kiểm (một lần torchrun 2 tiến trình, timeout 240 giây, dọn mọi tiến trình sau khi chạy). Gọi $$P$$ là số tham số của
`build_model()`:

- DDP, mỗi rank: `param_numel == grad_numel == P`, `optimizer_numel == 2P`.
- FSDP: tổng hai rank của `param_numel`, `grad_numel` bằng $$P$$, của `optimizer_numel` bằng $$2P$$; **mỗi** rank giữ trong khoảng 45-55%
  của tổng đó; `param_types` của cả hai rank là `["DTensor"]`.
- `model_state_bytes` của FSDP chia cho của DDP nằm trong 0.45-0.55 trên mỗi rank.
- `losses` của FSDP bằng của DDP ở mọi bước trên cùng rank (sai số tương đối 1e-4), và loss DDP rank 0 giảm từ bước đầu tới bước cuối.
- `wrap(model, "zero3")` báo `ValueError`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/15-distributed-training/exercises/intermediate/01-fsdp-shard-per-rank -q` pass.
- Bạn giải thích được vì sao hai rank FSDP giữ số tham số lệch nhau vài trăm phần tử.
- Bạn ước tính được bộ nhớ trạng thái mỗi GPU của model 7B trên 8 GPU với DDP, ZeRO-2 và FSDP full shard.

## Gợi ý

### Gợi ý 1

Chạy bản DDP trước (chỉ cần `wrap` và một `local_numel` đơn giản) rồi in `type(p)` và `p.shape` của tham số sau `fully_shard`.

### Gợi ý 2

Một `DTensor` biết kích thước toàn cục của nó; phần dữ liệu nằm trên rank hiện tại lấy bằng `to_local()`. `from torch.distributed.tensor import DTensor`.

### Gợi ý 3

Gradient của tham số FSDP cũng là `DTensor`, và optimizer state được tạo theo hình dạng của tham số, nên cùng một `local_numel` dùng được cho cả ba.
