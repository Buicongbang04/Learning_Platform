# Hướng làm và rubric: DDP, FSDP hay DeepSpeed cho model 7B

Rubric chấm phép tính và lập luận, không chấm việc chọn đúng một cái tên. FSDP và DeepSpeed ZeRO-3 đều có thể là đáp án tốt; DDP thì không.

## Hướng làm mẫu

**1. Bộ nhớ trạng thái model** (16 byte mỗi tham số: bf16 tham số và gradient, fp32 master, hai moment AdamW; $$\Psi = 7 \times 10^9$$):

| Chiến lược | 8 GPU | 32 GPU |
| --- | --- | --- |
| DDP | 112 GB (không vừa 80 GB) | 112 GB |
| ZeRO-1 ($$4 + 12/N$$ byte) | 38.5 GB | 30.6 GB |
| ZeRO-2 ($$2 + 14/N$$ byte) | 26.3 GB | 17.1 GB |
| ZeRO-3 / FSDP full shard ($$16/N$$ byte) | 14 GB | 3.5 GB |

Activation: với hidden 4 096, 32 layer, chuỗi 4 096, micro-batch 1 và attention dạng FlashAttention, mỗi layer giữ cỡ $$34 \cdot s \cdot h$$ byte,
khoảng 0.57 GB, cả model khoảng 18 GB mỗi chuỗi. Activation checkpointing toàn phần chỉ giữ đầu vào mỗi layer (cỡ 1 GB) và tính lại phần
còn lại khi backward (thêm khoảng 30% tính toán). Kết luận: ZeRO-2 trên 8 GPU (26 GB + 18 GB) hay ZeRO-3 (14 GB + 18 GB) vừa 80 GB với
micro-batch 1-2; DDP không bao giờ vừa.

**2. Thời gian.** 40 tỉ token / 3 000 token mỗi giây mỗi GPU = khoảng 3 700 GPU-giờ. 8 GPU: 463 giờ, 19 ngày, trễ hạn. 32 GPU với $$e = 0.8$$:
145 giờ, 6 ngày; với $$e = 0.5$$ (Ethernet giữa node làm chậm all-gather): 231 giờ, 9.6 ngày, sát hạn. Kiểm tra chéo: 3 000 token/giây
x $$6 \times 7 \times 10^9$$ FLOP = 126 TFLOP/s, khoảng 13% đỉnh bf16 của H100: MFU thấp. Tối ưu trên một node trước (FlashAttention, micro-
batch lớn hơn nhờ activation checkpointing, `torch.compile`) có thể gấp đôi thông lượng, rẻ hơn mọi node thêm vào.

**3. So sánh.**

| | DDP | FSDP2 | DeepSpeed ZeRO-3 (+offload) |
| --- | --- | --- | --- |
| Vừa bộ nhớ | không | có (14 GB/GPU trên 8) | có; offload chỉ cần khi GPU nhỏ |
| Giao tiếp mỗi bước | all-reduce gradient | all-gather x2 + reduce-scatter (khoảng 1.5x) | như FSDP; ZeRO++ giảm qua nén và shard phân cấp |
| Mạng giữa node chậm | tốt nhất | full shard 32 GPU qua Ethernet đau; hybrid shard giải quyết | hpZ (ZeRO++) giải quyết tương tự |
| Code và vận hành | đơn giản | PyTorch thuần, `fully_shard` mỗi block, DTensor | thêm thư viện và config JSON, launcher riêng |
| Checkpoint | `torch.save` | `torch.distributed.checkpoint` (shard) | định dạng riêng, cần chuyển đổi để serving |

**4. Quyết định.** FSDP2 với **hybrid sharding**: mesh 2 chiều (4 node x 8 GPU), shard trong node qua NVLink, replicate giữa node (giao tiếp
giữa node chỉ là all-reduce gradient đã shard, như DDP). Bộ nhớ trạng thái 14 GB mỗi GPU như full shard trên 8. Mỗi transformer block là
một đơn vị `fully_shard`; activation checkpointing mỗi block; bf16 với master fp32 (`MixedPrecisionPolicy`); batch toàn cục khoảng 4 triệu
token (micro-batch 2 x chuỗi 4 096 x 32 GPU x gradient accumulation 16), LR warmup. Lý do không chọn DeepSpeed: đội đã dùng PyTorch, không
cần offload, và hệ sinh thái (TorchTitan, torchtune) dùng FSDP2 trực tiếp; xem lại nếu phải chạy trên GPU nhỏ hơn cần offload.

**5. Hậu quả.** Checkpoint chuyển sang `torch.distributed.checkpoint` (mỗi rank ghi phần của mình, resume được với số GPU khác), có bước
gộp ra tệp `safetensors` đầy đủ cho serving; kiểm resume như bài Basic 02 trước khi chạy thật. Theo dõi: thông lượng token/giây/GPU, MFU,
thời gian all-gather so với tính toán, bộ nhớ đỉnh; alert khi treo (bài Intermediate 04). Xem lại quyết định khi có InfiniBand (full
shard trở nên rẻ), khi model lên 30B+ (cần tensor parallel trong node), hoặc khi chuyển sang LoRA (DDP đủ).

## Rubric (100 điểm)

| Mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Bộ nhớ | 25 | 16 byte/tham số; bảng 4 chiến lược ở 8 và 32 GPU đúng bậc; có activation và đòn bẩy giảm nó |
| Thời gian | 20 | GPU-giờ từ thông lượng; kết luận 8 GPU không kịp; nói hiệu suất scale qua Ethernet là rủi ro; có kiểm tra chéo MFU hoặc FLOP |
| So sánh | 20 | Ít nhất 4 tiêu chí, có mạng giữa node và checkpoint |
| Quyết định | 20 | Cấu hình cụ thể (đơn vị shard, hybrid hay full, checkpointing, batch); lý do gắn với bối cảnh đội |
| Hậu quả | 15 | Đổi pipeline checkpoint; theo dõi; điều kiện xem lại |

Mức đạt 70. Trừ điểm: chọn DDP vì "model 14 GB" (-20, nhầm inference với huấn luyện); full shard 32 GPU qua Ethernet mà không nhắc giao
tiếp giữa node (-10); không có phép tính thời gian (-10).
