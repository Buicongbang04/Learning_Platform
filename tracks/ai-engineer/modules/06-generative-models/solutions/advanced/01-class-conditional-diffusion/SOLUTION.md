# Hướng làm: diffusion sinh ảnh CIFAR-10 theo class

Bài không có code lời giải: model, vòng train và cách đánh giá là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả của một
bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Đưa class vào U-Net | `nn.Embedding(11, 4·ch)` cộng vào time embedding (đi vào mọi ResBlock) | rẻ, đủ cho 10 class; text thì cần cross-attention |
| Nhãn rỗng | hàng thứ 11 (chỉ số 10), $$p_{uncond} = 0.1$$ khi train | trùng một class thật thì nhánh rỗng không còn "không điều kiện" |
| Kiến trúc | ch 64, mults (1, 2, 2, 2), 2 ResBlock mỗi mức, GroupNorm, SiLU, attention ở 8×8 và giữa, dropout 0.1, upsample nearest + conv; 8 954 883 tham số | U-Net DDPM thu nhỏ; attention ở 16×16 đắt hơn 15% mà ngân sách 2 giờ không đủ để nó trả lãi |
| Schedule và mục tiêu | linear $$T = 1000$$, dự đoán $$\varepsilon$$ | đúng DDPM gốc; cosine hoặc $$v$$ là thí nghiệm tiếp theo hợp lý |
| Optimizer | AdamW lr 2e-4, warmup 1 000 bước, không weight decay, clip grad norm 1.0, batch 128 | cấu hình phổ biến của DDPM nhỏ |
| EMA | 0.9995 (cửa sổ khoảng 2 000 bước), lưu cả trọng số thô và EMA mỗi 5 000 bước | 0.9999 hợp với train dài hơn; với 35 000 bước, checkpoint sớm sẽ còn mang nhiều trọng số khởi tạo |
| Dữ liệu | 50 000 ảnh train trên GPU dạng uint8, lật ngang ngẫu nhiên, $$[-1, 1]$$ | không có DataLoader nào nhanh bằng dữ liệu đã nằm sẵn trên GPU (module 02) |
| Tăng tốc | bf16 autocast, `torch.compile` (biên dịch khoảng 1.5 phút) | 107 ms/bước so với 170 ms/bước không compile; VRAM 1.4 GB so với 2.6 GB |
| Sampler | DDIM 50 bước, kẹp $$\hat x_0$$, gộp hai nhánh CFG thành batch đôi | 20 lần ít forward hơn DDPM 1 000 bước |
| Giám khảo class | ResNet-20 train 30 epoch (SGD Nesterov, OneCycle, crop + flip) | test accuracy 0.9047; độc lập với model sinh |
| FID / KID | Inception-v3 torchvision `IMAGENET1K_V1`, pool 2048 chiều, resize bilinear 299, chuẩn hoá ImageNet; 5 000 ảnh sinh (500 mỗi class) so với 10 000 ảnh test | tái lập được offline sau một lần tải trọng số; **không** cùng trọng số với FID trong paper |

Những lỗi hay gặp khi làm bài: nhãn rỗng trùng class 0; quên label dropout rồi vẫn trộn CFG; tính FID với ảnh sinh ở $$[-1, 1]$$ còn ảnh thật ở $$[0, 1]$$;
lấy mẫu không cân bằng class (FID so với tập test cân bằng sẽ bị phạt oan); so FID của hai cấu hình khác số mẫu; sinh bằng model ở chế độ train
(dropout); đánh giá trọng số thô trong khi tưởng là EMA.

## Kết quả tham chiếu

PC: RTX 3060 12GB (GPU đang chia với một bài train khác), torch 2.14.1+cu126, seed 0. Train 35 000 bước (90 epoch) trong 61.8 phút. Sinh
5 000 ảnh, 500 mỗi class, cùng nhiễu ban đầu (seed 1234) cho mọi cấu hình, DDIM 50 bước, trọng số EMA.

Giám khảo ResNet-20: test accuracy 0.9047 trên ảnh CIFAR-10 thật. Mốc: 5 000 ảnh **train thật** so với 10 000 ảnh test cho FID **7.42**, KID
khoảng 0.

| Cấu hình | FID | KID × 1000 (± std) | Class accuracy | Thời gian sinh 5 000 ảnh |
| --- | --- | --- | --- | --- |
| Không điều kiện (nhãn rỗng) | 31.04 | 20.71 ± 1.31 | 0.101 | 100 s |
| $$w = 0$$ (có điều kiện, không guidance) | 26.17 | 16.34 ± 1.24 | 0.699 | 99 s |
| $$w = 0.5$$ | 21.98 | 11.32 ± 0.93 | 0.860 | 196 s |
| $$w = 1$$ | **20.52** | 8.45 ± 0.73 | 0.927 | 196 s |
| $$w = 2$$ | 22.11 | **6.58 ± 0.43** | 0.972 | 196 s |
| $$w = 4$$ | 30.41 | 8.27 ± 0.51 | 0.990 | 196 s |

Thí nghiệm phụ ($$w = 1$$):

| Thí nghiệm | Số mẫu | FID | KID × 1000 | Class accuracy |
| --- | --- | --- | --- | --- |
| EMA, 35 000 bước (dòng chính) | 5 000 | 20.52 | 8.45 ± 0.73 | 0.927 |
| Trọng số thô, 35 000 bước | 5 000 | 21.45 | 7.75 ± 0.60 | 0.898 |
| EMA, checkpoint 10 000 bước (ngân sách laptop) | 5 000 | 40.86 | 20.93 ± 0.98 | 0.715 |
| EMA, checkpoint 20 000 bước | 5 000 | 25.79 | 12.43 ± 0.91 | 0.870 |
| DDIM 10 bước | 2 000 | 41.70 | 20.13 ± 0.87 | 0.894 |
| DDIM 25 bước | 2 000 | 31.28 | 11.31 ± 0.70 | 0.919 |
| DDIM 100 bước | 2 000 | 26.37 | 6.91 ± 0.57 | 0.925 |

Mốc FID theo số mẫu (ảnh train thật so với 10 000 ảnh test): 1 000 ảnh **30.52**, 2 000 ảnh 15.44, 5 000 ảnh 7.42, 10 000 ảnh 4.95; KID của cả bốn
đều trong khoảng ±0.06 × 10⁻³ quanh 0.

Đọc kết quả, đây là phần quan trọng nhất của báo cáo:

- **Guidance là núm đánh đổi.** Class accuracy tăng đơn điệu theo $$w$$ (0.70 → 0.99), còn FID có dạng chữ U, tốt nhất ở $$w = 1$$ rồi tệ đi khi đa dạng
  mất dần ($$w = 4$$ cho 30.41, tệ ngang bản không điều kiện dù 99% ảnh đúng class). Đúng hình dạng của bài đồ chơi ở mục 6 lý thuyết và của bài báo CFG.
- **FID và KID không đồng ý về điểm tốt nhất** (FID chọn $$w = 1$$, KID chọn $$w = 2$$): hai thước đo cân chất lượng và đa dạng khác nhau. Báo cáo tốt nói ra
  điều này thay vì chọn thước đo nào cho số đẹp hơn. Chênh lệch KID giữa $$w = 1$$ và $$w = 2$$ (8.45 và 6.58) lớn hơn vài lần độ lệch chuẩn giữa các tập con.
- **Con số tuyệt đối phải đọc cùng mốc.** FID 20.5 trên 5 000 mẫu không so được với "FID 3.17" của DDPM trong paper (50 000 mẫu, Inception TensorFlow,
  so với tập train): chính ảnh thật với ảnh thật đã cho 7.42 ở 5 000 mẫu và 30.52 ở 1 000 mẫu. Bảng số bước DDIM dùng 2 000 mẫu nên FID của nó cao hơn
  dòng chính một phần chỉ vì ít mẫu; so số bước bằng KID (không chệch): 10 bước 20.1, 25 bước 11.3, 50 bước 8.5, 100 bước 6.9.
- **EMA** giúp class accuracy (0.927 so với 0.898) và FID một chút; KID lại hơi tốt hơn ở trọng số thô, nằm trong khoảng 1 std. Với EMA 0.9995 và lr cố
  định, khác biệt nhỏ; EMA 0.9999 với train dài hơn thường cho khác biệt rõ hơn.
- **Ngân sách laptop**: 10 000 bước cho FID 40.9 và class accuracy 0.71; 20 000 bước đã xuống 25.8. Đường cong còn đang giảm ở 35 000 bước: train lâu hơn
  là cải thiện rẻ nhất còn lại.
- Thời gian: train 61.8 phút (107 ms/bước, gồm cả biên dịch), classifier 3.5 phút, toàn bộ đánh giá khoảng 25 phút: tổng khoảng 1.5 giờ GPU. Sinh có
  guidance tốn gấp đôi ($$w \ne 0$$: hai nhánh mỗi bước).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Model và train | 15 | U-Net có điều kiện đúng (nhãn rỗng riêng, label dropout), EMA, checkpoint; ghi tham số, thời gian, VRAM |
| Đánh giá tái lập | 20 | FID/KID với cài đặt ghi rõ (trọng số, resize, số mẫu, tập thật), mẫu cân bằng class, cùng nhiễu giữa các cấu hình; mốc thật-với-thật |
| Quét guidance | 20 | Ít nhất 5 giá trị $$w$$ cộng bản không điều kiện; bảng FID, KID, class accuracy; chỉ ra đánh đổi chất lượng và đa dạng bằng số |
| Thí nghiệm phụ | 10 | Ít nhất hai (EMA, số bước, checkpoint sớm, mốc) với diễn giải |
| Diễn giải trung thực | 10 | Nói rõ FID ở đây không so được với paper và vì sao; phân biệt chênh lệch thật với nhiễu (KID có độ lệch chuẩn) |
| Chất lượng portfolio | 10 | Tóm tắt có số, lưới ảnh không chọn tay, lỗi đã gặp có triệu chứng và cách phát hiện, giới hạn và bước tiếp |

Đạt từ 70 điểm. Báo cáo chỉ có lưới ảnh đẹp mà không có chỉ số, hoặc so FID của mình với FID trong paper mà không nói khác cài đặt, không quá 50 điểm.
