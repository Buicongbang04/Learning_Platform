# Lời giải: pipeline dữ liệu CIFAR-10 nhanh và tái lập được

## Cách làm

**`decode_cifar_parquet`.** Đọc hai cột bằng `pyarrow.parquet.read_table`, decode mọi PNG bằng PIL thành mảng
`(N, 32, 32, 3)` uint8, rồi `torch.from_numpy(...).permute(0, 3, 1, 2).contiguous()`. `permute` đổi thứ tự trục (giữ
nguyên từng pixel), `contiguous()` sắp lại bộ nhớ để các bước sau (`view`, chép sang GPU) không phải làm. Dùng `reshape`
hay `view` thẳng sang `(N, 3, 32, 32)` cho đúng shape nhưng trộn pixel: test so từng pixel nên bắt được. Decode 50 000
ảnh mất khoảng 3.5 giây khi máy rảnh (tới 15 giây khi CPU đang bận), một lần; tensor uint8 nặng 150 MB.

**`CifarDataset`.** Giữ tensor uint8; `__getitem__` lấy một ảnh, nếu `augment` thì `F.pad(..., mode="reflect")` (cần
float), cắt tại `(dy, dx)` từ `self.rng.integers(0, 9, 2)`, lật với `self.rng.random() < 0.5`, rồi chuẩn hoá. Augment
trên uint8/float trước khi chuẩn hoá để reflect pad lấy đúng giá trị pixel.

**`seed_worker` và `make_loader`.** `get_worker_info().dataset` là bản sao dataset trong worker; tạo lại
`rng = np.random.default_rng(torch.initial_seed() % 2**32)`. `torch.initial_seed()` trong worker bằng `base_seed + worker_id`,
mà `base_seed` sinh từ `generator` truyền cho `DataLoader`: cùng seed thì cùng mọi thứ, worker khác nhau thì dòng số khác
nhau. Thiếu `generator`, `base_seed` lấy từ RNG toàn cục, nên hai lần chạy khác nhau dù code giống hệt.

**`augment_batch`.** Pad cả batch một lần, sinh `dy, dx` shape `(N,)` và cờ lật, dựng chỉ số hàng
`dy[:, None] + arange(H)` (shape `(N, H)`) rồi `gather` theo chiều 2, chỉ số cột tương tự theo chiều 3, lật bằng
`torch.where`. Không có vòng lặp Python theo ảnh, nên chạy trên GPU với cả batch trong vài kernel. Số ngẫu nhiên sinh trên CPU
từ `generator` (tái lập được bất kể device) rồi chuyển sang device của `x`.

## Kết quả thật

Thông lượng của lời giải trên CIFAR-10 thật (batch 256, CPU 16 luồng đang có tải nặng từ tiến trình khác, nên đọc như tỉ
lệ; bảng đầy đủ ở mục 3 lý thuyết): decode PNG trong `__getitem__` với 0 worker 235 ảnh/giây; tensor đã decode + augment từng
ảnh 643 ảnh/giây với 0 worker, 15 438 với 4 worker; `augment_batch` cả batch trên CPU một tiến trình 8 590 ảnh/giây. Decode
một lần là cải thiện lớn nhất và rẻ nhất; worker nhân tiếp; còn với GPU thì đưa cả tập lên GPU và dùng `augment_batch` bỏ
hẳn nút thắt CPU (bài Intermediate 01 làm vậy).

Bộ thật: tập test 10 000 ảnh, đúng 1 000 ảnh mỗi lớp, 8 nhãn đầu `[3, 8, 8, 0, 6, 6, 1, 6]`; tập train 50 000 ảnh, 5 000 mỗi lớp.

## Bẫy thường gặp

- `self.rng = np.random.default_rng(seed)` mà không có `worker_init_fn`: với 2 worker, batch 0 và batch 1 (16 ảnh giống
  nhau) trùng nhau từng pixel. Không có lỗi nào, chỉ là augmentation lặp lại theo chu kỳ số worker. Dùng `torch.randint`
  trong `__getitem__` thì không gặp (PyTorch tự seed `torch` cho từng worker), nhưng phải hiểu vì sao.
- Seed worker bằng hằng số (`default_rng(worker_id)`): khác nhau giữa worker nhưng **giống nhau giữa các epoch** khi
  `persistent_workers=False` (worker sinh lại với cùng seed mỗi epoch).
- Pad bằng 0 thay vì reflect: viền đen là tín hiệu giả mà model học được; test so với bản pad reflect.
- Decode PNG trong `__getitem__` mỗi epoch: đúng nhưng chậm, và tốn CPU mà GPU đang cần.
- `pin_memory=True` khi không có CUDA: PyTorch cảnh báo và bỏ qua; lời giải chỉ bật khi `torch.cuda.is_available()`.
