# Lời giải: sparse autoencoder trên residual stream của GPT-2 small

## Cách làm

**`SparseAutoencoder`.** Bốn tham số; `W_dec` rút từ generator riêng rồi chuẩn hoá hàng, `W_enc` là **bản sao** của `W_dec.T` (khởi
tạo "tied" giúp latent bắt đầu gần như một phép chiếu có nghĩa; dùng chung bộ nhớ thì hai ma trận bị ràng buộc suốt quá trình train).
`encode` trừ `b_dec` trước (nên `b_dec` học được "trung bình" của activation và latent mô tả độ lệch quanh nó). TopK: `pre.topk(k)` rồi
`scatter` giá trị đã qua ReLU vào tensor 0 (ReLU sau topk tương đương topk sau ReLU, chỉ khác khi có ít hơn k giá trị dương). `loss`:
MSE là **tổng** bình phương theo chiều (trung bình theo hàng), để thang loss không phụ thuộc $$d$$ theo cách lạ; L1 nhân norm hàng decoder.

**`activation_scale`.** $$c = \sqrt{d / \mathbb{E}\lVert x\rVert^2}$$, tính bằng float32 (bình phương float16 tràn khi norm cỡ vài nghìn).

**`train_sae`.** Batch ngẫu nhiên có hoàn lại bằng một generator riêng (tái lập, không phụ thuộc trạng thái RNG toàn cục), chuẩn hoá
decoder sau mỗi `opt.step()`, lr hằng rồi giảm tuyến tính về 0 ở 20% cuối.

**`sae_metrics`.** Cộng dồn theo batch: $$\sum\lVert x - \hat x\rVert^2$$, $$\sum x$$, $$\sum\lVert x\rVert^2$$ (float64), số latent bật, và mặt nạ "đã
từng bật" OR qua mọi batch. Phương sai quanh trung bình $$= \sum\lVert x\rVert^2 - \lVert\sum x\rVert^2/N$$. Chia cho $$\sum\lVert x\rVert^2$$ thay vì
phương sai là lỗi kinh điển: residual stream có trung bình khác 0 lớn, FVU giả sẽ đẹp hơn thật nhiều lần.

**`collect_resid_pre`, `sae_splice`, `ce_loss_recovered`.** Pre-hook trên `blocks[layer]` (stream trước `ln1`), cắt `[:, 1:]`, `half()`
rồi `cpu()` từng batch để không giữ cả tập trên GPU. Splice thay `x[:, 1:]` bằng `sae(x * c)[0] / c` và giữ vị trí 0: SAE không train
trên vị trí 0 (norm lớn gấp khoảng 40 lần) nên không được dùng ở đó.

Cài sai đã thử và bị test bắt: không trừ `b_dec`, TopK không qua ReLU, MSE trung bình theo chiều, L1 không nhân norm decoder,
`W_enc` ngẫu nhiên độc lập, quên chuẩn hoá decoder, không giảm lr, bỏ qua `scale`, FVU không trừ trung bình, đếm latent chết theo từng
batch, giữ vị trí 0, thu stream sau `ln1`, quên chia `scale` khi splice, splice cả vị trí 0, đảo công thức CE recovered.

## Kết quả thật

Ngày 2026-11-01, torch 2.14.1, seed 0. Dữ liệu đồ chơi chạy trên CPU ở cả hai cấu hình nên số giống nhau.

### Dữ liệu đồ chơi (30 hướng trong 10 chiều, mỗi đặc trưng bật với xác suất 0.05)

| SAE (60 latent, 1 500 bước) | FVU | L0 | Cosine tốt nhất với 30 hướng thật: trung bình / nhỏ nhất |
| --- | --- | --- | --- |
| TopK k = 3 | 0.090 | 3.0 | 0.980 / 0.931 |
| ReLU + L1 0.05 | 0.019 | 11.8 | 0.940 / 0.770 |

L1 tái dựng tốt hơn (FVU 0.019) nhưng dùng gần 12 latent cho mỗi mẫu trong khi trung bình chỉ 1.5 đặc trưng thật đang bật, và tìm
lại các hướng kém hơn: FVU thấp không có nghĩa là từ điển đúng. TopK với k vừa đủ tìm lại cả 30 hướng (nhỏ nhất 0.93).

### GPT-2 small, residual stream vào Block 6

Activation: IWSLT15 `train.en` (TED), ngữ cảnh 128 token, bỏ vị trí 0; đánh giá trên `tst2012.en` + `tst2013.en` (56 642 token). Norm
stream tầng 6: vị trí 0 trung bình 3 029, các vị trí khác 77.6; `scale` = 0.354. CE trên tập đánh giá: model gốc 3.383, zero ablation
tầng 6 là 10.109, mean ablation 7.095.

**Cấu hình GPU** (1 000 125 token, 6 144 latent, 976 bước batch 4 096; RTX 3060 của PC dùng chung với tiến trình khác, cả notebook 247
và 395 giây ở hai lần chạy, VRAM dưới 2 GB; thu activation 47 giây, mỗi SAE khoảng 43 giây):

| SAE | FVU | L0 | Latent chết | CE ghép SAE | Recovered (zero) | Recovered (mean) |
| --- | --- | --- | --- | --- | --- | --- |
| TopK k = 32 | 0.188 | 32.0 | 10.0% | 3.539 | 0.977 | 0.958 |
| L1 2.0 | 0.351 | 64.8 | 0.0% | 4.008 | 0.907 | 0.832 |
| L1 5.0 | 0.860 | 10.4 | 1.3% | 6.372 | 0.556 | 0.195 |


**Cấu hình CPU** (200 025 token, 3 072 latent, 195 bước batch 4 096; cả notebook 1 121 giây, khoảng 19 phút, đo khi PC đang tải nặng,
load average khoảng 15):

| SAE | FVU | L0 | Latent chết | CE ghép SAE | Recovered (zero) | Recovered (mean) |
| --- | --- | --- | --- | --- | --- | --- |
| TopK k = 32 | 0.391 | 32.0 | 8.0% | 4.156 | 0.885 | 0.792 |
| L1 2.0 | 0.653 | 166.9 | 0.0% | 5.511 | 0.684 | 0.427 |
| L1 5.0 | 1.103 | 46.5 | 0.2% | 7.691 | 0.359 | −0.161 |

Đọc kết quả:

- Ở cùng ngân sách nhỏ (vài trăm tới một nghìn bước), TopK thắng rõ cả tái dựng lẫn độ trung thành; L1 cần dò hệ số và train lâu hơn
  nhiều. L1 5.0 có FVU trên 0.8 ở cả hai cấu hình: phạt quá mạnh so với số bước, và ghép vào làm CE tệ gần bằng (GPU: 6.37 so với 7.10) hoặc
  tệ hơn (CPU: 7.69) mean ablation. Đây là kết
  luận về **ngân sách này**, không phải về L1 nói chung.
- Đổi baseline từ zero sang mean ablation làm "recovered" của cùng một SAE giảm rõ (TopK: 0.977 xuống 0.958 trên GPU, 0.885 xuống 0.792 trên CPU). Báo CE tuyệt đối: TopK làm CE tăng 0.16 nat (GPU) và
  0.77 nat (CPU, ít dữ liệu hơn), con số mà "97.7%" che đi.
- TopK có latent chết (latent không lọt top-k lần nào), L1 hầu như không; ngược lại L1 2.0 dùng 65 (GPU) tới 167 (CPU) latent mỗi token.
- Latent (SAE TopK, cấu hình GPU, 6 latent ngẫu nhiên có mật độ từ $$10^{-4}$$ tới $$10^{-2}$$; token kích hoạt trong ngoặc vuông): latent
  3177 bật ở "[ average]" sau " the"/" an"; latent 172 ở token "D"/"d" (C.[D]., I.[D]., [D]iclofenac, [d]itches); latent 2861 ở danh từ
  quảng bá, cổ động ([ marketing], [ slogans], [ stickers], [ chants]); latent 3170 ở vị ngữ ngay sau "answer was/is" ([ yes], [ correlation]);
  latent 5611 lẫn lộn (token đầu của tên riêng, thương hiệu, từ hiếm: [ Gary], [ Disney], [ Microsoft], [ hipp]os). Latent thứ sáu
  (3094, [ neighbor]) rất sạch. Bốn trên sáu đặt tên được ngay, một polysemantic rõ, một ở giữa. Top activation chỉ cho thấy latent bật
  mạnh **ở đâu** trên tập đánh giá; nó không cho thấy latent bật yếu ở đâu, có gây ra hành vi gì không, hay tên gọi có đúng trên dữ liệu
  khác không. Lần chạy CPU (SAE khác) cho các latent khác; số thứ tự latent không so được giữa hai SAE.

## Bẫy thường gặp

- Để vị trí 0 trong dữ liệu train: vài hàng norm 3 000 chi phối MSE.
- Quên `scale` hoặc tính nó trên float16.
- Báo FVU không kèm L0, hoặc báo CE recovered không nói baseline.
- Đọc latent chỉ bằng 5 ví dụ mạnh nhất rồi đặt tên chắc nịch.
