# Lời giải: điểm nghẽn nạp dữ liệu

`loader_bench.py` cạnh tệp này là lời giải chạy được.

## Số đo mẫu (máy thử bài, đang chạy việc khác)

| `num_workers` | `wait_fraction` | chẩn đoán | mẫu/giây |
| --- | --- | --- | --- |
| 0 | khoảng 0.62 | data | khoảng 300 |
| 1 | khoảng 0.40 | data | khoảng 480 |
| 2 | dưới 0.05 | compute | khoảng 780 |
| 4 | dưới 0.05 | compute | khoảng 780 |

Từ 2 lên 4 worker gần như không thêm gì: điểm nghẽn đã chuyển sang bước huấn luyện (16 mẫu / 20 ms = 800 mẫu/giây là trần).

## Ý chính

- **Đo chờ và tính riêng.** Chỉ đo tổng thời gian mỗi bước thì không biết chậm vì đâu. Thời gian quanh `next(iterator)` là thời gian GPU
  ngồi không; thời gian quanh `step` là việc thật.
- **Ba con số đủ để đoán trước.** Một batch tốn 16 x 2 = 32 ms giải mã. Không worker: mỗi bước 32 + 20 ms, chờ chiếm 62%. 1 worker chạy
  song song với vòng huấn luyện: batch sẵn sàng mỗi 32 ms, bước dùng 20 ms, còn chờ 12 ms (38%). 2 worker: một batch mỗi 16 ms, nhanh hơn
  bước 20 ms, prefetch luôn có hàng sẵn, chờ gần 0.
- **Bỏ warmup.** Khởi động worker (fork, nạp dataset) mất hàng trăm ms; tính vào thì 4 worker trông chậm hơn 2 worker trong job ngắn. Job
  dài nhiều epoch: `persistent_workers=True` để chỉ trả chi phí này một lần.
- **Chọn số nhỏ nhất đủ dùng.** Mỗi worker là một tiến trình giữ một bản dataset và một core. Với 8 rank DDP trên node 64 core,
  `num_workers=16` mỗi rank là 128 tiến trình giành 64 core, chậm hơn `num_workers=6`.
- **GPU bất đồng bộ.** Lệnh CUDA trả về ngay khi đã xếp hàng; không `torch.cuda.synchronize()` trước khi bấm giờ thì thời gian bước GPU
  thật bị tính vào lần chờ dữ liệu tiếp theo, và bạn chẩn đoán nhầm là nghẽn dữ liệu.

## Khi thêm worker không cứu được

Tổng CPU của cả node không đủ giải mã (ảnh JPEG lớn, augmentation nặng) thì phải giảm việc: giải mã trên GPU (NVIDIA DALI), lưu sẵn ở
độ phân giải nhỏ hơn, cache tensor đã tiền xử lý, hoặc đẩy tiền xử lý sang cụm CPU riêng (Ray Data). Đọc triệu tệp nhỏ từ object
storage thì gộp thành shard lớn (WebDataset, Parquet) để đọc tuần tự.
