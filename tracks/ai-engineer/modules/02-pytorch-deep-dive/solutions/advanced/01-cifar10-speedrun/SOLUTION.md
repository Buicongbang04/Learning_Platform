# Hướng làm: CIFAR-10 94% trên GPU 4GB

Bài không có code lời giải: thiết kế pipeline và thí nghiệm là phần của bạn. Dưới đây là các quyết định cần cân nhắc, kết
quả của một bản tham chiếu (giữ ngoài repo) để bạn so, và rubric chấm.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Model | ResNet-9 (Page 2018): conv-BN-ReLU 64 → 128 (+pool, residual) → 256 (+pool) → 512 (+pool, residual) → max pool toàn cục → `Linear(512, 10, bias=False)` × 0.125; 6.57 triệu tham số | đủ sức đạt 94%, nông nên nhanh; nhân 0.125 giữ logits nhỏ lúc đầu như một temperature |
| Dữ liệu | cả tập uint8 nằm trên GPU (150 MB), xáo bằng `randperm` trên GPU | không `DataLoader`, không chép CPU → GPU mỗi bước; GPU không bao giờ chờ |
| Augmentation | crop ngẫu nhiên sau pad reflect 4 + lật ngang, theo batch trên GPU (`augment_batch` bài Basic 03) | hai phép đủ cho 94%; vectorized nên gần như miễn phí |
| Số học | autocast bf16, `channels_last`, loss trên logits `.float()` | gần 2× nhanh hơn fp32 (mục 4), không cần GradScaler |
| Optimizer | SGD Nesterov momentum 0.9, batch 512, weight decay 5e-4 chỉ cho tham số ≥ 2 chiều | công thức đã kiểm chứng cho ResNet trên CIFAR; AdamW không nhanh hơn ở đây |
| Lịch lr | tam giác theo bước, peak 0.4, warmup 20% | lr lớn ở giữa cho tốc độ, về 0 ở cuối để "lắng" |
| Regularization | label smoothing 0.2 | train ngắn mà vẫn tổng quát tốt; giảm tự tin quá mức |
| Đánh giá | TTA lật ngang (trung bình logits ảnh và ảnh lật) | +0.4–0.7 điểm gần như miễn phí |
| Đo | `torch.cuda.synchronize()` quanh vòng train; `max_memory_allocated` sau `reset_peak_memory_stats` | thời gian GPU thật; peak là thứ quyết định OOM |
| Log | giữ loss là tensor trên GPU, `.item()` một lần mỗi epoch | mỗi `.item()` ép CPU chờ GPU, phá việc xếp hàng kernel |

Những lỗi hay gặp: tính lr theo epoch thay vì theo bước (lr nhảy bậc, kém hơn); đặt `channels_last` cho model nhưng quên cho
input (cuDNN đổi layout mỗi bước); đo thời gian không `synchronize` (con số đẹp giả); dữ liệu fp32 trên GPU (586 MB thay vì
150 MB, cộng activation là vượt ngân sách 1.5 GB: bản tham chiếu đã OOM như vậy ở lần chạy đầu khi GPU có tiến trình khác);
chọn số epoch bằng cách nhìn test accuracy.

## Kết quả tham chiếu

Bản tham chiếu theo đúng bảng trên, batch 512, bf16, RTX 3050 Laptop 4GB, torch 2.14.1+cu126. Thời gian là vòng train (có
`synchronize`), không tính decode dữ liệu và đánh giá. GPU dùng chung: lần seed 0 chạy khi GPU chỉ có một tiến trình khác
đang giữ bộ nhớ mà không tính; seed 1, 2 chạy cùng lúc với một bài train khác nên chậm gấp đôi.

| Epoch | Seed | Thời gian train | Peak | Test acc (không TTA) | Test acc (TTA lật) |
| --- | --- | --- | --- | --- | --- |
| 10 | 0 | 146 s | 1 330 MiB | 0.9194 | 0.9232 |
| 16 | 0 | 237 s | 1 330 MiB | 0.9316 | 0.9357 |
| 24 | 0 | 341 s | 1 330 MiB | 0.9373 | **0.9437** |
| 24 | 1 | 751 s (GPU bận) | 1 330 MiB | 0.9376 | **0.9436** |
| 24 | 2 | 658 s (GPU bận) | 1 330 MiB | 0.9382 | **0.9426** |

- **24 epoch là đủ cho 94%**: trung bình 94.33% qua 3 seed (min 94.26%), dao động giữa seed khoảng 0.1 điểm. 16 epoch thiếu
  0.4–0.8 điểm; mỗi epoch khoảng 14 giây khi GPU rảnh.
- **TTA lật ngang** thêm 0.4–0.7 điểm, tốn một lần forward thêm trên tập test (vài giây).
- **Peak 1 330 MiB** dưới ngân sách 1.5 GB: tập train uint8 150 MB, model và trạng thái SGD khoảng 75 MB, phần còn lại là
  activation bf16 của batch 512. Bỏ AMP (fp32) với cùng batch 512 thì **OOM** trên GPU dùng chung (PyTorch đã cấp 1.71 GiB khi
  hỏng): không có mixed precision thì phải giảm batch, và mục tiêu thời gian xa hơn.
- Lần chạy đầu tiên của bản tham chiếu giữ cả tập train ở **fp32 đã chuẩn hoá** trên GPU (586 MB) và OOM ngay khi GPU có tiến
  trình khác: lưu uint8, chuẩn hoá từng batch.
- Thời gian thay đổi gấp đôi theo việc GPU có ai dùng: báo cáo phải ghi điều kiện đo, và so ablation trong cùng điều kiện.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | Mọi test pass |
| Mục tiêu | 20 | ≥ 94% trung bình 3 seed, peak ≤ 1.5 GB; thời gian train ghi rõ cách đo. Thiếu một trong hai: tối đa 10 |
| Thiết lập tái lập được | 10 | Kiến trúc, siêu tham số, seed, phần cứng, phiên bản torch, cách đo thời gian và bộ nhớ; không chọn gì theo test |
| Ablation | 20 | Ít nhất 4 thành phần, mỗi lần bỏ một, cùng ngân sách; có độ phân tán seed ở cấu hình chính |
| Diễn giải và profiler | 20 | Tách "làm nhanh" (AMP, layout, dữ liệu trên GPU) khỏi "làm chính xác" (label smoothing, TTA, lịch lr); đọc trace đúng (GPU chờ hay không, kernel lớn nhất, có kernel đổi layout không); nói rõ chênh lệch nào trong dao động seed |
| Chất lượng portfolio | 20 | Tóm tắt có số ở đầu, hình loss có câu đọc, mục ngõ cụt có triệu chứng và cách phát hiện, giới hạn và bước tiếp |

Đạt từ 70 điểm. Báo cáo chỉ có một lần chạy một seed, hoặc thời gian đo không `synchronize`, không quá 50 điểm.
