---
title: Chọn DDP, FSDP hay DeepSpeed cho model 7B
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Ra một quyết định kỹ thuật có số cho bài toán thật: fine-tune toàn bộ model 7 tỉ tham số trên cụm GPU có sẵn, so DDP, FSDP và DeepSpeed
ZeRO theo bộ nhớ, giao tiếp, độ phức tạp vận hành, và viết thành một bản ghi quyết định (ADR) mà đồng nghiệp review được. Không có test;
tự chấm bằng rubric trong `SOLUTION.md`.

## Đề bài

Bối cảnh: đội cần fine-tune toàn bộ tham số (không LoRA) một LLM 7B trên 40 tỉ token dữ liệu nội bộ, mixed precision bf16 với AdamW,
độ dài chuỗi 4 096, mục tiêu xong trong 10 ngày. Hạ tầng có sẵn:

- 4 node, mỗi node 8 GPU H100 80 GB nối NVLink; giữa node là Ethernet 100 Gb/s (không InfiniBand).
- Đội đã dùng PyTorch, chưa ai vận hành DeepSpeed; pipeline checkpoint hiện tại là `torch.save` một tệp.
- Throughput đo được trên một node với một cấu hình thử: khoảng 3 000 token/giây mỗi GPU.

Viết `ADR.md` (tối đa 2 trang):

1. **Phép tính bộ nhớ** mỗi GPU cho DDP, ZeRO-1, ZeRO-2, ZeRO-3/FSDP full shard trên 8 GPU và trên 32 GPU (trạng thái model; nói
   activation chiếm thêm bao nhiêu và đòn bẩy nào giảm nó).
2. **Phép tính thời gian**: số GPU-giờ cần cho 40 tỉ token, có kịp 10 ngày không với 8 và 32 GPU, giả định hiệu suất scale qua Ethernet.
3. **So sánh** DDP / FSDP / DeepSpeed ZeRO (có offload) theo: vừa bộ nhớ không, giao tiếp mỗi bước, phù hợp mạng giữa node, độ phức tạp
   code và vận hành, checkpoint.
4. **Quyết định** và cấu hình cụ thể (đơn vị shard, shard trong node hay toàn cụm, activation checkpointing, kích thước batch toàn cục).
5. **Hậu quả**: phải đổi gì trong pipeline checkpoint, theo dõi gì, khi nào xem lại quyết định.

## Tiêu chí đạt

- `ADR.md` đủ 5 mục; phép tính bộ nhớ và thời gian đúng bậc độ lớn.
- Tự chấm theo rubric `SOLUTION.md` đạt từ 70/100.
- Bạn trả lời được "vì sao không dùng DDP với 8 GPU 80 GB cho model chỉ 14 GB ở bf16".

## Gợi ý

### Gợi ý 1

Bảng ZeRO ở mục 3 README module cho bộ nhớ trạng thái mỗi GPU theo $$N$$. Activation của transformer tỉ lệ với batch x độ dài chuỗi x số
layer x hidden; activation checkpointing đổi khoảng 30% tính toán lấy phần lớn bộ nhớ đó.

### Gợi ý 2

FSDP full shard trên 32 GPU all-gather tham số qua Ethernet giữa node mỗi bước. Tìm hiểu hybrid sharding (shard trong node, replicate
giữa node: `HYBRID_SHARD` ở FSDP1, mesh 2 chiều ở FSDP2).
