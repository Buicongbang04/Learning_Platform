# Lời giải: LeNet, ResNet và ViT tự dựng, train trên CIFAR-10

## Cách làm

**Dữ liệu.** `pd.read_parquet`, giải mã từng PNG bằng `Image.open(io.BytesIO(...)).convert("RGB")`, `np.stack` thành
`(N, 32, 32, 3)` uint8. Nhãn `to_numpy(dtype=np.int64, copy=True)`: pandas 3 trả mảng chỉ-đọc, `torch.from_numpy` sẽ cảnh
báo. `channel_stats` trải về `(-1, 3)` rồi `mean`/`std` theo trục 0 ở float64. `to_tensor` dùng `permute(0, 3, 1, 2)`:
`reshape` sang `(N, 3, H, W)` cũng ra đúng shape nhưng trộn pixel của ba kênh, model vẫn "học" và chỉ kém đi.

**Augmentation.** `F.pad` 4 pixel số 0 (ở không gian đã chuẩn hoá, 0 là màu trung bình), rút `oy`, `ox` trong `0..8` và
cờ lật cho **từng** ảnh từ `generator`, cắt và `flip(-1)` theo từng ảnh. Vòng lặp Python qua ảnh trong batch 128 tốn vài
ms, nhỏ so với forward; bản vector hoá dùng `unfold` hoặc chỉ số gather nếu cần nhanh hơn.

**LeNet-5 và ResNet.** LeNet: hai khối conv 5×5 + ReLU + max pool, `Flatten` (400), ba tầng Linear: 62 006 tham số, 95% nằm ở
Linear. `BasicBlock`: hai conv 3×3 không bias, BN sau mỗi conv, shortcut identity khi giữ shape, conv 1×1 stride `s` + BN
khi đổi; `out = relu(bn2(conv2(relu(bn1(conv1(x))))) + shortcut(x))`, `residual=False` bỏ phép cộng. `ResNetCifar`: stem,
`3n` block (stride 2 ở block đầu của stage 2 và 3), `mean(dim=(2, 3))` làm global average pooling, `Linear(64, C)`.

**ViT.** `PatchEmbed` là `Conv2d(in_ch, dim, patch, stride=patch)` rồi `flatten(2).transpose(1, 2)`: patch xếp theo hàng rồi
cột. Attention: `qkv(x).reshape(B, N, 3, heads, d_h).permute(2, 0, 3, 1, 4)` tách `q, k, v` thành `(B, heads, N, d_h)`;
`softmax(q @ kᵀ / √d_h) @ v`, rồi `transpose(1, 2).reshape(B, N, D)` ghép head và `proj`. Thứ tự `reshape` phải khớp cách
`qkv` xếp output `[q | k | v]`, mỗi phần các head liền nhau. Block pre-norm, CLS token ghép đầu chuỗi, position embedding
cộng sau khi ghép, LayerNorm cuối, head đọc vector CLS.

**Vòng train.** `torch.manual_seed(seed)` và một `torch.Generator` seed `seed` cho cả xáo dữ liệu lẫn augmentation; AdamW;
OneCycleLR với `total_steps = epochs * ceil(N / batch)` và `sched.step()` **sau mỗi** `opt.step()`. Loss epoch cộng
`loss.item() * len(batch)` rồi chia `N` (batch cuối nhỏ hơn không bị tính nặng như batch đủ). Kết thúc bằng `model.eval()`.
`evaluate` dưới `@torch.no_grad()`, gọi `eval()` để BatchNorm dùng running stats: không có nó, accuracy phụ thuộc cỡ batch
đánh giá.

## Kết quả thật

Tham số và phép nhân-cộng mỗi ảnh 32×32 (đếm bằng `torch.utils.flop_counter`): LeNet-5 62 006 / 0.65 triệu, ResNet-20
272 474 / 40.8 triệu, ResNet-56 855 770 / 125.7 triệu, ViT d128×6 811 146 / 58.0 triệu. Thống kê kênh của 50 000 ảnh train:
mean `(0.4914, 0.4822, 0.4465)`, std `(0.2470, 0.2435, 0.2616)`.

**Kernel `ai-gpu`, PC RTX 3060**, đủ 50 000 ảnh, 15 epoch, seed 0, AdamW (lr 3e-3 cho CNN, 1e-3 cho ViT, weight decay
0.05), batch 128. Train acc đo trên 10 000 ảnh train không augment. GPU lúc đo đang chạy song song một bài train khác,
nên cột thời gian chỉ để thấy cỡ, không để so từng dòng:

| Model | s/epoch | Loss train cuối | Train acc | Test acc |
| --- | --- | --- | --- | --- |
| LeNet-5 | 4.4 | 0.966 | 0.689 | 0.682 |
| Plain-20 | 58.4 | 0.377 | 0.882 | 0.850 |
| ResNet-20 | 107.8 | 0.295 | 0.907 | 0.868 |
| ResNet-20 không augment | 32.2 | 0.033 | **0.997** | 0.848 |
| ViT d128×6, patch 4 | 21.2 | 0.604 | 0.798 | 0.757 |
| Plain-56 (mở rộng, chỉ GPU) | 44.5 | 0.936 | 0.685 | 0.661 |
| ResNet-56 (mở rộng, chỉ GPU) | 63.5 | 0.239 | 0.927 | 0.882 |

«CPU_INT01»

Đọc kết quả:

- **Residual**: ở 20 tầng, Plain-20 kém ResNet-20 khoảng 2 điểm; ở 56 tầng, Plain-56 tụt hẳn cả train acc (0.685) trong khi
  ResNet-56 tốt nhất bảng. Degradation là chuyện tối ưu, không phải overfit.
- **Augmentation**: bỏ random crop + lật, ResNet-20 học thuộc tập train (train acc 0.997, loss 0.033) mà test acc giảm 2
  điểm; khoảng cách train/test nở từ 0.04 lên 0.15. Với augmentation, mô hình thấy mỗi ảnh ở vị trí và hướng khác nhau
  mỗi epoch nên khó học thuộc.
- **ViT**: nhiều tham số gấp 3 ResNet-20 mà thua 11 điểm, và train acc cũng thấp hơn (0.798 so với 0.907): ở quy mô này ViT
  **học chậm** chứ không học thuộc. Không có giả định cục bộ của conv, nó phải tự học từ dữ liệu rằng pixel gần nhau liên
  quan với nhau; 50 000 ảnh và 15 epoch không đủ. Đây là lý do ViT thường dùng ở dạng pretrain lớn (mục 3 lý thuyết).
- **Tốc độ**: số tham số không dự đoán được thời gian. ResNet-20 có 4.4 lần tham số của LeNet-5 nhưng 63 lần phép tính, và
  chậm hơn nhiều lần trên cả CPU lẫn GPU. Trên GPU dùng chung, thời gian còn phụ thuộc tiến trình khác: đo lại khi máy rảnh
  trước khi kết luận về tốc độ.

## Bẫy thường gặp

- `reshape` thay `permute` khi đổi NHWC sang NCHW: shape đúng, nội dung bị xáo, không lỗi nào.
- ReLU trong nhánh trước phép cộng, hoặc shortcut projection ở mọi block: vẫn train được, chỉ lệch kiến trúc đã kiểm chứng
  (test so số tham số và công thức).
- Attention `reshape(B, N, heads, 3, d_h)`: chạy được, nhưng mỗi "head" là một lát cắt lẫn lộn của q, k, v.
- Quên chia $$\sqrt{d_h}$$: softmax bão hoà sớm, gradient nhỏ, ViT học chậm hơn hẳn.
- `scheduler.step()` mỗi epoch với OneCycleLR đặt theo bước: lr gần như đứng ở mức warmup suốt quá trình train.
- Đánh giá ở chế độ train: BatchNorm chuẩn hoá theo batch test, kết quả đổi theo `batch_size`.
