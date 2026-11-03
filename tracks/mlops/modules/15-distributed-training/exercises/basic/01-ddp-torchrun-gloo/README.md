---
title: DDP với torchrun trên CPU (gloo)
level: basic
services: []
files:
  - path: starter/train_ddp.py
    note: 5 hàm TODO; phần còn lại (dữ liệu, model, vòng lặp, ghi log) có sẵn
  - path: tests/test_ddp.py
    note: Không sửa
run:
  - uv run python -m torch.distributed.run --nproc_per_node=2 --rdzv-backend=c10d --rdzv-endpoint=127.0.0.1:0 --local-addr=127.0.0.1 tracks/mlops/modules/15-distributed-training/exercises/basic/01-ddp-torchrun-gloo/starter/train_ddp.py --out /tmp/mlops-15/ddp
  - uv run pytest tracks/mlops/modules/15-distributed-training/exercises/basic/01-ddp-torchrun-gloo -q
---

## Mục tiêu

Chạy một job huấn luyện hai tiến trình bằng `torchrun`, backend gloo trên CPU, và chứng minh bằng số rằng DDP làm đúng việc của nó:
mỗi rank thấy phần dữ liệu riêng, tham số hai rank giống hệt nhau sau mỗi bước, loss giảm, và kết quả bằng huấn luyện một tiến trình
trên batch toàn cục.

## Đề bài

`starter/train_ddp.py` có sẵn dữ liệu sinh theo `SEED`, model MLP, vòng huấn luyện SGD và phần ghi log. Điền 5 hàm:

- `setup()`: khởi tạo process group backend `gloo` từ biến môi trường mà torchrun đặt; trả `(rank, world_size, local_rank)`.
- `make_loader(dataset, rank, world)`: `DataLoader` batch `BATCH_PER_RANK` mà mỗi rank chỉ thấy phần của mình, xáo theo `SEED`, bỏ phần
  lẻ cuối (`drop_last`); trả `(loader, sampler)`.
- `wrap(model)`: bọc model để gradient được đồng bộ giữa các rank.
- `start_epoch(sampler, epoch)`: gọi đầu mỗi epoch để mỗi epoch có thứ tự xáo khác.
- `teardown()`: huỷ process group.

Không đổi hằng số, `make_dataset`, `build_model`, `param_digest` hay định dạng log. Mỗi rank ghi:

- `<out>/rank<r>-meta.json`: `{"rank", "local_rank", "world_size", "backend"}`.
- `<out>/rank<r>.jsonl`: mỗi bước một dòng `{"step", "epoch", "loss", "digest", "indices"}` (`digest` là băm tham số **sau** bước,
  `indices` là chỉ số mẫu của batch).
- `<out>/rank<r>-final.pt`: `state_dict` của model gốc (đã bỏ lớp bọc).

Luật mà test kiểm (chạy `torchrun --nproc_per_node=2 ... --steps 60`, timeout 240 giây, dọn mọi tiến trình sau khi chạy):

- Meta của rank `r` là đúng `{"rank": r, "local_rank": r, "world_size": 2, "backend": "gloo"}`.
- Cả hai rank ghi đủ 60 bước, `digest` hai rank bằng nhau ở **mọi** bước.
- Trong cùng một bước, hai rank không dùng chung mẫu nào, mỗi batch đúng `BATCH_PER_RANK` mẫu; epoch đầu đi qua mỗi mẫu đúng một lần;
  thứ tự epoch 1 khác epoch 0.
- Loss trung bình hai rank của 10 bước cuối nhỏ hơn 0.6 lần của 5 bước đầu.
- Huấn luyện **một tiến trình** từ cùng khởi tạo, mỗi bước trên batch gộp hai rank (loss MSE trung bình, SGD cùng `LR`), cho tham số
  khớp `rank0-final.pt` (sai số tuyệt đối 1e-4).

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/15-distributed-training/exercises/basic/01-ddp-torchrun-gloo -q` pass.
- Bạn giải thích được vì sao "tham số hai rank giống nhau" chưa đủ để kết luận DDP đúng (và test nào bắt phần còn lại).
- Bạn nói được `RANK` khác `LOCAL_RANK` ở đâu khi job chạy trên 2 node, mỗi node 4 GPU.

## Gợi ý

### Gợi ý 1

`dist.init_process_group(backend="gloo")` không cần tham số khác khi chạy dưới torchrun: địa chỉ, cổng, rank và world size đều nằm
trong biến môi trường. `LOCAL_RANK` đọc từ `os.environ`.

### Gợi ý 2

`DistributedSampler(dataset, num_replicas=world, rank=rank, shuffle=True, seed=SEED, drop_last=True)` rồi truyền `sampler=` cho
`DataLoader` (khi đã có sampler thì không truyền `shuffle`).

### Gợi ý 3

Nếu loss giảm, digest khớp mà test so với một tiến trình vẫn fail, xem lại bạn đồng bộ gradient bằng tổng hay trung bình.
