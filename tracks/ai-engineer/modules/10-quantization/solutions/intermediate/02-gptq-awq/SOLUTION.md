# Lời giải: GPTQ và AWQ tự cài trên GPT mini

## Cách làm

**`capture_inputs`.** Forward hook nhận `(module, inputs, output)`; `inputs[0]` là tensor `(B, T, in)`, reshape thành
`(B·T, in)`, đưa về float32 trên CPU, thêm vào list của lớp đó. Chạy model ở chế độ eval trong `torch.no_grad()`, gỡ hook trong
`finally` (một lỗi giữa chừng không để lại hook treo trên model), trả lại chế độ train/eval cũ.

**`hessian`.** $$H = \frac{2}{N}X^\top X$$ trong float64, cộng $$\lambda I$$ với $$\lambda$$ = 1% trung bình đường chéo (giống
`damp_percent=0.01` của các công cụ GPTQ). Dampening tương đối vì độ lớn của $$X$$ khác nhau giữa các lớp; một kênh luôn bằng 0
(hay gặp sau ReLU, hoặc ở token đặc biệt) làm $$H$$ suy biến, Cholesky thất bại.

**`gptq_quantize`.** Ba bước của đề, viết thẳng:

```text
U = cholesky(cholesky_inverse(cholesky(H)), upper=True)
với j = 0 .. in-1:
    nếu j % group_size == 0: scale, zero = quant_params(W[:, j:j+g])   # W đã được cập nhật
    Q[:, j] = quant_column(W[:, j], scale, zero)
    e = (W[:, j] - Q[:, j]) / U[j, j]
    W[:, j+1:] -= outer(e, U[j, j+1:])
```

Vì sao đúng: hàng $$j$$ của $$U$$ chia cho $$U_{jj}$$ bằng hàng $$j$$ của $$H^{-1}$$ **sau khi đã loại các cột 0..j-1** chia cho
phần tử đường chéo của nó (tính chất của khử Gauss trên ma trận đối xứng xác định dương). Nên dòng cập nhật chính là công thức OBS
$$\delta = -\frac{w_j - q_j}{[H^{-1}]_{jj}}[H^{-1}]_{j,:}$$ áp lên các cột còn tự do, mà không phải cập nhật $$H^{-1}$$ sau mỗi cột.
Kiểm bằng ví dụ 2 cột: $$U_{01}/U_{00} = [H^{-1}]_{01}/[H^{-1}]_{00} = -H_{01}/H_{11}$$, nên cột 1 nhận thêm
$$(w_0 - q_0)H_{01}/H_{11}$$, đúng thứ test tính tay. Với $$H = I$$, $$U = I$$, không có cập nhật nào: GPTQ trùng RTN.

Tham số nhóm phải tính từ trọng số **đã cập nhật** khi tới cột đầu nhóm: các cột trong nhóm đã nhận phần bù từ các nhóm trước,
scale tính từ trọng số gốc sẽ không còn khớp và mã bị kẹp.

**`awq_scales` / `awq_quantize`.** $$s = m^{\alpha}$$ chuẩn hoá bằng $$\sqrt{\max s\cdot\min s}$$ (để scale quanh 1, không đẩy toàn
bộ ma trận lên hay xuống). Với mỗi $$\alpha \in \{0, 0.05, \dots, 0.95\}$$: trọng số hiệu dụng `rtn_quantize(W * s) / s`, sai số
đầu ra trung bình bình phương trên $$X$$, giữ $$\alpha$$ tốt nhất (so sánh `<` nghiêm ngặt nên hoà giữ $$\alpha$$ nhỏ, và
$$\alpha = 0$$ chính là RTN nên AWQ không bao giờ tệ hơn RTN **trên dữ liệu hiệu chỉnh**).

**`apply_layerwise`.** `copy.deepcopy`, rồi với mỗi lớp `weight.copy_(quantize_fn(name, W, X))` trong `torch.no_grad()`.

## Đơn giản hoá so với bản gốc

- Input của mọi lớp được ghi **một lần** từ model float (không tuần tự): GPTQ gốc lượng tử hoá từng khối Transformer rồi mới ghi
  input cho khối sau từ model đã lượng tử một phần, để lớp sau bù được cả sai số của lớp trước. Bản tham chiếu Qwen trong phần lý
  thuyết dùng cách tuần tự.
- Không có act-order, không có lazy batch (cùng kết quả, chậm hơn), AWQ không tìm ngưỡng cắt (clip) và không gộp scale vào lớp trước
  (đo trên trọng số hiệu dụng, tương đương về số học).

## Kết quả tham chiếu

Notebook lời giải chạy bằng kernel GPU (đánh giá đủ 100 bài validation; GPTQ/AWQ chạy trên CPU), 32 đoạn hiệu chỉnh từ 200 bài
train đầu, seed 0. Thời gian lượng tử hoá đo trên PC đang bận, chỉ so thô.

| Cấu hình | Phương pháp | PC: bpc (Δ) | Laptop: bpc (Δ) | PC: thời gian |
| --- | --- | --- | --- | --- |
| int4 nhóm 128 đối xứng | RTN | 1.3683 (+0.0211) | 1.5584 (+0.0189) | 0.1 s |
| | GPTQ | 1.3595 (+0.0123) | 1.5492 (+0.0097) | 8.8 s |
| | AWQ | 1.3689 (+0.0218) | 1.5591 (+0.0195) | 13.4 s |
| int3 nhóm 128 đối xứng | RTN | 1.4747 (+0.1276) | 1.6543 (+0.1148) | 0.1 s |
| | GPTQ | 1.4256 (+0.0784) | 1.5991 (+0.0596) | 8.9 s |
| | AWQ | 1.4793 (+0.1321) | 1.6509 (+0.1113) | 14.9 s |
| int3 nhóm 32 zero-point | RTN | 1.3898 (+0.0426) | 1.5800 (+0.0404) | 0.2 s |
| | GPTQ | 1.3714 (+0.0243) | 1.5597 (+0.0202) | 9.0 s |
| | AWQ | 1.3856 (+0.0384) | 1.5778 (+0.0382) | 14.9 s |

(Nguồn: `logs/nb_gptq_gpu_pc.log`, `nb_gptq_gpu_laptop.log`, notebook đã chạy trong `executed/`.)

- **GPTQ** bớt khoảng 40-50% Δ của RTN ở mọi cấu hình, ở cả hai checkpoint (int3 nhóm 128: 39% ở PC, 48% ở laptop). Đổi seed
  hiệu chỉnh (1, 2) làm bpc GPTQ lệch dưới 0.002 (`logs/gptq_seeds.log`), nhỏ hơn nhiều so với khoảng cách tới RTN.
- **AWQ ngang RTN** (chênh dưới 0.005 bpc, có cấu hình còn tệ hơn một chút). Lý do nằm ở cell thống kê activation: tỉ lệ max/median
  của trung bình $$\lvert x\rvert$$ theo kênh lớn nhất chỉ 22.2 (PC, `blocks.2.attn.qkv`) và 10.5 (laptop), phần lớn các lớp dưới 10.
  Qwen2.5-0.5B ở phần lý thuyết lên tới 154 và AWQ bớt khoảng 40% Δ ở đó. AWQ chỉ làm được điều nó được thiết kế cho: bảo vệ kênh
  activation trội. Thêm nữa, AWQ chọn $$\alpha$$ tốt nhất trên dữ liệu hiệu chỉnh từng lớp riêng lẻ; một chút lợi ở sai số đầu ra
  từng lớp không nhất thiết chuyển thành bpc tốt hơn.
- **Sai số trọng số và sai số đầu ra** (int3 nhóm 128, 4 lớp đầu): GPTQ có sai số trọng số **lớn hơn** RTN 1.4-1.8 lần, nhưng sai
  số đầu ra **nhỏ hơn** 1.6-3.3 lần (PC: `blocks.0.mlp.proj` 2.06e-2 → 6.48e-3). GPTQ cố tình đẩy trọng số xa giá trị gốc theo
  hướng mà đầu ra trên dữ liệu thật không đổi. Đánh giá một phương pháp quantize bằng khoảng cách trọng số là đo sai thứ.
- Checkpoint dự phòng: cùng xu hướng (GPTQ bớt 63% Δ ở int3 nhóm 128, AWQ ngang RTN) nhưng mọi Δ đều nhỏ (dưới 0.007), vì model
  train quá ngắn gần như không có ngoại lai (tỉ lệ activation lớn nhất 3.6).

## Bẫy thường gặp

- Hiệu chỉnh trên chính validation: GPTQ khớp sai số trên dữ liệu đó, bpc validation lạc quan giả tạo.
- Quên dampening hoặc dùng $$\lambda$$ tuyệt đối: Cholesky lỗi ở lớp có kênh chết, hoặc dampening quá mạnh ở lớp có activation nhỏ
  (biến GPTQ về RTN).
- Tính tham số nhóm từ trọng số gốc: mã bị kẹp ở các nhóm sau, GPTQ tệ hơn RTN ở bit thấp.
- Duyệt cột ngược hoặc cập nhật cả các cột đã quantize: test 3 cột tính tay bắt được ngay.
