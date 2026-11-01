# Lời giải: Post-training quantization cho GPT mini

## Cách làm

**`fake_quantize_weight`.** Ba mức chia scale quy về một shape `(hàng, số khối, cỡ khối)`: per-tensor `(1, 1, out·in)`,
per-channel `(out, 1, in)`, theo nhóm `(out, in/g, g)`. Trên trục cuối của shape đó áp đúng công thức absmax hoặc zero-point của bài
Basic 01 (khoảng chứa 0, zero-point nguyên, kẹp, khối toàn 0 dùng scale 1), rồi `reshape` về `(out, in)`. Không vòng lặp nào.

**`quantize_model`.** `copy.deepcopy` để model gốc không đổi, rồi với mỗi `nn.Linear` có trọng số **không** phải trọng số của một
`nn.Embedding` (trừ khi `include_embedding=True`), `weight.copy_(...)` trong `torch.no_grad()`. Sửa tại chỗ bằng `copy_` giữ nguyên
đối tượng tensor, nên `lm_head.weight is tok_emb.weight` vẫn đúng trong bản sao (`deepcopy` giữ quan hệ dùng chung), và embedding
được quantize đúng một lần (mỗi hàng là một token: per-channel của `lm_head` cũng là per-token của embedding).

**`weight_storage_bytes`.** Duyệt `model.parameters()` (tự bỏ tensor dùng chung lặp lại); tensor được quantize tốn
`numel·bits/8` cộng 2 byte mỗi scale (thêm 1 byte zero-point nếu bất đối xứng), phần còn lại 4 byte mỗi phần tử.

**`layer_sensitivity`.** Đo model gốc một lần; với mỗi tên, `deepcopy`, `get_submodule(name).weight.copy_(quantize_fn(...))`, đo
lại, ghi hiệu. Đây là "one-at-a-time sensitivity", rẻ và đủ để chọn lớp giữ nhiều bit; nó bỏ qua tương tác giữa các lớp.

## Kết quả tham chiếu

Hai checkpoint của module 05 (cấu hình PC 13.8 triệu tham số, `n_embd` 384; cấu hình laptop 5.3 triệu tham số, `n_embd` 256),
đủ 100 bài validation (664 568 ký tự), cửa sổ trượt 256/128 như module 05, đánh giá trên GPU (bpc không phụ thuộc thiết bị tới
chữ số thứ 4). Chỉ các lớp Linear trong khối; embedding/`lm_head` dùng chung giữ float32 trừ dòng ghi khác.

| Cấu hình | PC: bpc | PC: Δ | PC: MB | Laptop: bpc | Laptop: Δ | Laptop: MB |
| --- | --- | --- | --- | --- | --- | --- |
| float32 | 1.3472 | | 55.27 | 1.5395 | | 21.09 |
| int8 per-tensor | 1.3473 | +0.0002 | 23.42 | 1.5398 | +0.0003 | 11.66 |
| int8 per-channel | 1.3473 | +0.0002 | 23.46 | 1.5395 | +0.0000 | 11.67 |
| int8 per-channel + embedding | 1.3474 | +0.0002 | 14.26 | 1.5396 | +0.0001 | 5.55 |
| int4 per-tensor | 1.6364 | +0.2893 | | 1.6667 | +0.1272 | |
| int4 per-channel | 1.3793 | +0.0321 | 18.15 | 1.5645 | +0.0250 | 10.10 |
| int4 per-channel, zero-point | 1.3689 | +0.0218 | | 1.5579 | +0.0184 | |
| int4 nhóm 128 | 1.3683 | +0.0211 | 18.28 | 1.5584 | +0.0189 | 10.13 |
| int4 nhóm 128 + embedding | 1.3794 | +0.0322 | 7.57 | 1.5723 | +0.0328 | 3.00 |
| int4 nhóm 32 | 1.3616 | +0.0144 | 18.78 | 1.5528 | +0.0133 | 10.28 |
| int4 nhóm 32, zero-point | 1.3557 | +0.0085 | 19.11 | 1.5483 | +0.0087 | 10.38 |
| int3 per-channel | 1.5392 | +0.1921 | | 1.6880 | +0.1485 | |
| int3 nhóm 32 | 1.4274 | +0.0802 | | 1.6108 | +0.0712 | |
| int3 nhóm 32, zero-point | 1.3898 | +0.0426 | 17.78 | 1.5800 | +0.0405 | 9.98 |
| int2 nhóm 32 | 2.4785 | +1.1314 | | 2.3626 | +0.8231 | |
| int2 nhóm 32, zero-point | 1.6458 | +0.2987 | 16.45 | 1.8174 | +0.2779 | 9.59 |

(Nguồn: `logs/ptq_gpu.log`, `logs/storage_mb.log` của bản tham chiếu; MB tính bằng `weight_storage_bytes`; Δ tính trên số chưa
làm tròn.)

Đọc bảng:

- **8 bit miễn phí** ở cả hai checkpoint, kể cả per-tensor và kể cả embedding.
- **4 bit: mức chia quyết định.** Per-tensor mất gấp 9 lần (PC) và 5 lần (laptop) per-channel. Nhóm 32 tốt hơn per-channel khoảng
  một nửa Δ, đổi lại 0.5 bit/trọng số cho scale.
- **Zero-point thắng ở bit thấp**: int4 per-channel bớt khoảng 30% Δ, int3 nhóm 32 bớt một nửa, int2 nhóm 32 bớt 3-4 lần. Lý do là
  số mức: absmax 2 bit chỉ có $$\{-1, 0, 1\}$$ (ternary), zero-point có 4 mức đặt theo $$[\min, \max]$$ của nhóm.
- **Embedding là phần lớn dung lượng** của model nhỏ: với Linear ở int4 nhóm 128, embedding float32 chiếm 12.3 trên 18.3 MB (PC).
  Quantize nó int4 cắt dung lượng 2.4 lần (PC) và 3.4 lần (laptop), bpc chỉ tăng thêm 0.011-0.014. Ở int8 thì gần như không mất gì.

Bảng trên lấy từ notebook lời giải chạy bằng kernel GPU (`logs/nb_ptq_gpu_*`) và một script đánh giá riêng cho các dòng notebook
không in (int4 per-tensor/per-channel + embedding nhóm 128); hai nguồn trùng nhau tới chữ số thứ 4. Cell embedding của notebook
dùng nhóm 32: dung lượng 18.78 → 8.22 MB (PC) và 10.28 → 3.24 MB (laptop), bpc tăng thêm 0.0071 và 0.0099.

### Ngoại lai trọng số và độ nhạy từng lớp

Tỉ lệ `max|w|/std` từ 4.8 tới 16.3 (PC) và 4.5 tới 9.4 (laptop); với phân phối chuẩn và vài trăm nghìn phần tử, giá trị này khoảng
5 (các lớp `mlp.fc` nằm đúng ở đó). Các lớp `attn.qkv`, `attn.proj` ở khối giữa và `mlp.proj` có đuôi dài nhất: đúng loại ma trận mà một scale per-tensor bị
ngoại lai chiếm.

Độ nhạy với int3 per-channel (quantize một lớp, các lớp khác float32):

| | PC | Laptop |
| --- | --- | --- |
| Ba lớp nhạy nhất | `blocks.2.attn.qkv` +0.0199, `blocks.1.attn.qkv` +0.0150, `blocks.0.mlp.proj` +0.0144 | `blocks.1.attn.qkv` +0.0187, `blocks.0.mlp.proj` +0.0169, `blocks.0.mlp.fc` +0.0142 |
| Ít nhạy nhất | các `attn.proj` (+0.0008 tới +0.0033) | các `attn.proj` (+0.0031 tới +0.0046) |
| Tổng các Δ riêng lẻ / Δ khi quantize tất cả | +0.1638 / +0.1921 | +0.1399 / +0.1485 |
| Giữ 2 / 4 lớp nhạy nhất ở int8 | +0.1580 / +0.1214 | +0.1167 / +0.0817 |

Tổng các Δ riêng lẻ nhỏ hơn Δ khi quantize cùng lúc: sai số của các lớp cộng hưởng qua residual stream, nên đo từng lớp là ước
lượng lạc quan, đủ để **xếp hạng** chứ không đủ để dự đoán. Giữ 4 trên 24 lớp ở int8 (thêm khoảng 1.3 MB ở PC) lấy lại khoảng 37%
(PC) và 45% (laptop) của Δ: mixed precision là cách rẻ nhất để chọn điểm giữa hai mức bit.

### Checkpoint dự phòng

Bản dự phòng (4 tầng, `n_embd` 128, 600 bước trên CPU, bpc float32 2.3438) gần như **không** mất gì khi lượng tử hoá: int4
per-tensor +0.0039, int3 nhóm 32 zero-point +0.0028, int2 nhóm 32 đối xứng +0.0652. Model train quá ngắn có trọng số gần với khởi
tạo ngẫu nhiên, ít ngoại lai và ít thông tin trên mỗi tham số; model train kỹ (checkpoint module 05, và hơn nữa Qwen2.5 ở phần lý
thuyết) mới cho thấy cái giá thật. Trắc nghiệm của bài giả định checkpoint của module 05.

## Bẫy thường gặp

- Quantize `lm_head` "vô tình" vì nó là một `nn.Linear`: embedding đầu vào đổi theo mà không ai để ý; hoặc ngược lại, gán
  `lm_head.weight = nn.Parameter(...)` mới làm vỡ weight tying và model to thêm một ma trận.
- Đếm dung lượng bằng `numel × bits / 8` mà quên scale (nhóm 32 thêm 11%) và quên rằng tensor không quantize vẫn ở float32.
- So bpc trên tập khác nhau (20 bài CPU với 100 bài GPU): chỉ so Δ trong cùng một lần chạy.
- Kết luận "int4 an toàn" từ một model: Qwen2.5-0.5B (phần lý thuyết) mất 0.2 bpc ở cùng cấu hình RTN nhóm 128.
