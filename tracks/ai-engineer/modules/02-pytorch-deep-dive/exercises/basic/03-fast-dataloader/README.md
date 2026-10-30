---
title: Pipeline dữ liệu CIFAR-10 nhanh và tái lập được
level: basic
services: []
files:
  - path: starter/data.py
    note: 1 lớp, 4 hàm TODO
  - path: tests/test_data.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cifar10
  - uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/basic/03-fast-dataloader -q
---

## Mục tiêu

Dựng pipeline dữ liệu cho CIFAR-10 mà các bài sau dùng lại: decode ảnh **một lần**, `Dataset` có augmentation,
`DataLoader` nhiều worker mà vẫn tái lập được theo seed, và augmentation chạy cho **cả batch** trên GPU. Làm xong
bạn biết vì sao GPU hay ngồi chờ dữ liệu, và tránh được bug "mọi worker augment giống hệt nhau".

## Đề bài

**Phần cứng:** CPU · ~75 phút

Sửa `starter/data.py` (mục 3 lý thuyết). Bộ `cifar10` là parquet của Hugging Face: cột `img` là dict có `bytes`
(ảnh PNG), cột `label`.

1. `decode_cifar_parquet(path)`: decode mọi ảnh một lần thành tensor `uint8 (N, 3, 32, 32)` contiguous và nhãn
   `int64`. PIL trả ảnh dạng `(H, W, C)`.
2. `CifarDataset(images, labels, augment, seed)`: `__getitem__` trả ảnh float đã chuẩn hoá theo mean/std của
   CIFAR-10 và nhãn `int`; `augment=True` thì pad reflect 4 pixel, cắt ngẫu nhiên 32×32, lật ngang xác suất 0.5,
   mọi số ngẫu nhiên lấy từ `self.rng` (numpy `Generator`).
3. `seed_worker(worker_id)`: `worker_init_fn` tạo lại `rng` của dataset trong từng worker từ `torch.initial_seed()`.
4. `make_loader(dataset, batch_size, shuffle, num_workers, seed)`: cùng seed thì cùng thứ tự **và** cùng
   augmentation, kể cả với nhiều worker; `pin_memory` khi có CUDA, `persistent_workers` khi có worker.
5. `augment_batch(x, generator, pad=4)`: cùng phép crop + flip nhưng cho cả batch `(N, C, H, W)` một lần, không vòng
   lặp Python theo ảnh, chạy được khi `x` nằm trên GPU.

## Tiêu chí đạt

- Decode đúng ảnh và nhãn trên parquet nhỏ sinh trong test (so từng pixel, nên `view` thay cho `permute` bị bắt); trên
  bộ thật: tập test 10 000 ảnh, 1 000 ảnh mỗi lớp, 8 nhãn đầu `[3, 8, 8, 0, 6, 6, 1, 6]`.
- `CifarDataset` chuẩn hoá đúng; mỗi ảnh augment là một crop (có thể lật) của bản pad reflect; cùng seed cùng kết quả.
- Với 2 worker và 16 ảnh giống hệt nhau, batch của worker 0 khác batch của worker 1; hai loader cùng seed cho cùng
  batch từng pixel, seed khác cho thứ tự khác.
- `augment_batch` giữ dtype, mỗi ảnh là crop/flip của chính nó, tỉ lệ lật trong khoảng 60–140 trên 200 ảnh, cùng
  generator cùng kết quả.

## Gợi ý

### Gợi ý 1

`DataLoader` với `num_workers > 0` fork tiến trình con, mỗi con có **bản sao** của dataset, kể cả `self.rng`: cùng
trạng thái thì cùng dãy số. PyTorch tự seed `torch`, `random` và `np.random` toàn cục cho từng worker, nhưng không biết
gì về `Generator` bạn tự tạo. Trong `seed_worker`, `torch.utils.data.get_worker_info().dataset` là bản sao của worker
đó; `torch.initial_seed()` khác nhau giữa các worker và phụ thuộc `generator` của `DataLoader`.

### Gợi ý 2

`augment_batch`: `F.pad(x.float(), (pad,) * 4, mode="reflect")`; sinh `dy`, `dx` shape `(N,)`, dựng chỉ số hàng
`dy[:, None] + arange(H)` rồi `gather` theo chiều 2, tương tự chiều 3; lật bằng
`torch.where(flip.view(N, 1, 1, 1), out.flip(3), out)`. Ép về dtype gốc ở cuối.
