# Lời giải: DDP với torchrun trên CPU (gloo)

`train_ddp.py` cạnh tệp này là lời giải chạy được.

## Ý chính

- **torchrun làm phần "tìm nhau".** Nó chạy rendezvous rồi đặt `RANK`, `LOCAL_RANK`, `WORLD_SIZE`, `MASTER_ADDR`, `MASTER_PORT` cho
  từng worker; `init_process_group("gloo")` đọc hết từ đó. Trên 2 node x 4 GPU, `RANK` chạy 0-7 trên cả job, `LOCAL_RANK` chạy 0-3 trong
  mỗi node và là chỉ số GPU (`cuda:LOCAL_RANK`).
- **`DistributedSampler` chia dữ liệu, `set_epoch` đổi thứ tự.** Sampler xáo bằng seed `SEED + epoch` rồi rank `r` lấy các vị trí
  `r, r + world, ...`. Không gọi `set_epoch` thì epoch nào cũng cùng thứ tự: model vẫn học, chỉ kém hơn một chút, nên lỗi này hay lọt qua
  review.
- **DDP = broadcast lúc bọc + all-reduce trung bình mỗi bước.** Hai điều đó làm mọi rank giữ cùng tham số. Nhưng "giống nhau" chưa phải
  "đúng": nếu cả hai rank cùng dùng một batch (quên sampler) hoặc cộng gradient mà không chia số rank, tham số vẫn giống nhau mà kết quả
  sai. Vì vậy test so với huấn luyện một tiến trình trên batch gộp: DDP với loss trung bình trên mỗi rank và gradient trung bình bằng
  đúng gradient của loss trung bình trên batch toàn cục.
- **Lưu `model.module`, không lưu lớp bọc.** `state_dict` của DDP có tiền tố `module.`; checkpoint như vậy không nạp được vào model thường
  (khi serving, khi chạy một tiến trình).

## Lỗi hay gặp

- Truyền cả `shuffle=True` lẫn `sampler=` cho `DataLoader`: PyTorch báo lỗi vì hai cái loại trừ nhau.
- Gọi `init_process_group` với `world_size`/`rank` tự điền cố định: chạy được với 2 tiến trình, treo khi đổi `--nproc_per_node`.
- Ghi log từ mọi rank vào cùng một tệp: dòng chen nhau. Mỗi rank một tệp, hoặc chỉ rank 0 ghi.
- Quên `destroy_process_group`: PyTorch cảnh báo và có lúc tiến trình thoát chậm vì luồng nền của gloo.
