# Lời giải: đo bộ nhớ theo rank, DDP và FSDP

`shard_report.py` cạnh tệp này là lời giải chạy được.

## Số đo (2 rank, MLP 148 481 tham số, Adam)

| | rank 0 tham số | rank 1 tham số | optimizer state mỗi rank | `model_state_bytes` mỗi rank |
| --- | --- | --- | --- | --- |
| DDP | 148 481 | 148 481 | 296 962 | 2.38 MB |
| FSDP | 74 369 | 74 112 | 148 738 / 148 224 | 1.19 MB |

Loss từng bước của FSDP trùng DDP tới chữ số cuối: shard đổi **chỗ để** trạng thái, không đổi phép toán.

## Ý chính

- **FSDP2 chia từng tham số theo chiều 0.** Trọng số `Linear(256, 256)` thành hai mảnh 128 x 256. Chiều 0 lẻ (bias của lớp cuối có 1
  phần tử, `Linear(256, 1)` có 1 hàng) thì một rank giữ phần dư, rank kia giữ ít hơn; đó là lý do 74 369 và 74 112. Tổng vẫn đúng 148 481.
- **`numel()` của `DTensor` là kích thước toàn cục.** Đo bằng `p.numel()` thì FSDP "giữ" 100% trên mỗi rank và bạn kết luận sai rằng
  FSDP không tiết kiệm gì. Phần thật sự trên rank là `p.to_local()`. Cùng bẫy với gradient (`p.grad` là `DTensor`) và optimizer state
  (Adam tạo `exp_avg` theo hình dạng tham số, nên cũng là `DTensor`).
- **Gọi `fully_shard` từng khối rồi model gốc.** Mỗi lần gọi tạo một đơn vị all-gather: trước forward của khối, các rank gom đủ tham số
  khối đó, dùng xong thì bỏ. Chỉ gọi cho model gốc vẫn shard đúng (test vẫn pass) nhưng cả model thành một đơn vị: lúc forward mọi tham
  số được gom cùng lúc, đỉnh bộ nhớ gần bằng DDP. Với transformer, mỗi block là một đơn vị.
- **Từ số đo sang 7B.** 16 byte mỗi tham số (mixed precision Adam): DDP 112 GB mỗi GPU (không vừa); ZeRO-2 trên 8 GPU
  $$2 + 14/8 = 3.75$$ byte, khoảng 26 GB; FSDP full shard $$16/8 = 2$$ byte, 14 GB, chưa kể activation. Bài Advanced 02 dùng đúng phép tính này.

## Ở đây không đo được gì

- Đỉnh bộ nhớ thật trên GPU (`torch.cuda.max_memory_allocated`) gồm cả tham số đang được all-gather, activation, bộ đệm giao tiếp; số
  "trạng thái model" ở đây là phần ổn định, không phải đỉnh.
- Chi phí giao tiếp: FSDP all-gather tham số hai lần mỗi bước (forward và backward) cộng reduce-scatter, khoảng 1.5 lần DDP. Trên CPU
  gloo không thấy rõ; trên cụm GPU nhiều node thì thấy.
