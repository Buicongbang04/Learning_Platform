# Hướng làm: mini framework numpy trên MNIST

Bài không có code lời giải: framework là thiết kế của bạn. Dưới đây là các quyết định thiết kế cần cân nhắc,
kết quả của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Gradient nằm ở đâu | `Param(data, grad, decay)`; layer ghi `grad` trong `backward` | optimizer chỉ duyệt `model.parameters()`, không cần biết layer |
| Weight decay cho ai | `decay=True` chỉ cho `W` của `Linear`; bias, `gamma`, `beta` là `False` | kéo bias hay `gamma` về 0 không chống overfit mà chỉ làm lệch chuẩn hoá |
| Lưu "trọng số tốt nhất" | `state()` = tham số + running mean/var; chụp bằng `.copy()`, nạp bằng `a[...] = s` | thiếu running stats thì BatchNorm ở eval dùng thống kê của epoch cuối với trọng số của epoch khác |
| Chế độ train/eval | `Sequential.train(mode)` lan xuống mọi layer; `evaluate` tự chuyển eval rồi trả lại chế độ cũ | quên eval làm accuracy phụ thuộc cách chia batch |
| Schedule | cosine theo **bước**, tổng số bước = `epochs * ceil(N / batch)` | lr giảm mượt tới 0 ở bước cuối; theo epoch thì lr nhảy bậc |
| Tái lập | mọi rng (init, dropout, xáo) sinh từ `seed` của `build_model` | cùng seed cho đúng cùng history, so ablation mới công bằng |
| dtype | float32 cho dữ liệu và tham số, float64 khi gradient check | float32 nhanh hơn và tốn nửa bộ nhớ; sai phân hữu hạn cần float64 |

Những lỗi hay gặp khi viết: `backward` của `Sequential` không đi ngược thứ tự; `Dropout` sinh mask mới trong
`backward`; `EarlyStopping` lưu tham chiếu thay vì bản sao (`snapshot = model.state()`), nên "bản tốt nhất" luôn
trùng trọng số hiện tại; gán `p.data = p.data - ...` trong optimizer làm `Param` trỏ mảng mới (vô hại ở đây
nhưng phá mọi tham chiếu khác tới mảng cũ); batch cuối chỉ 1 mẫu làm BatchNorm báo lỗi (50 000 / 128 dư 80, an
toàn; batch khác thì nên bỏ batch dưới 2 mẫu).

Test "bẫy thuộc lòng" bắt được hai lỗi khó thấy: không nạp lại bản tốt nhất (val sau `fit` 0.647 thay vì 0.920)
và chụp thiếu running stats (0.913 thay vì 0.920). Test chia nhóm 5 ảnh bắt `evaluate` ở chế độ train (239 so
với 289 ảnh đúng trên 300).

## Kết quả tham chiếu

MLP 784-512-256-10, BatchNorm + ReLU + dropout 0.2 sau mỗi tầng ẩn, AdamW lr 2e-3 weight decay 0.05, cosine
không warmup, batch 128, patience 3. Train 50 000 ảnh đầu, val 10 000 ảnh còn lại, test 10 000 ảnh. numpy
float32, `OMP_NUM_THREADS=4`, CPU i7-11800H.

- Test chấm (10 epoch, seed 0): **0.9853**, khoảng 22 giây.
- Model chính trong notebook (15 epoch, seed 0): best val 0.9853 ở epoch 12, test 0.9844, khoảng 30 giây; cả
  notebook kèm ablation khoảng 4 phút. Train loss 0.229 ở epoch 1, 0.0055 ở epoch 15; early stopping không kích
  hoạt (val còn nhích tới epoch 12, patience 3).
- Gradient check mạng nhỏ (Linear, BatchNorm train, ReLU, Linear, loss; float64): sai lệch dưới 1e-6.
- Baseline để đặt kết quả vào bối cảnh: đoán lớp nhiều nhất 0.1135; MLP 784-128-10 SGD 3 epoch (bài
  Intermediate 01) 0.9636; Adam 3 epoch (mục 6 lý thuyết) 0.9747.

Ablation, 10 epoch, seed 0 / 1, test accuracy:

| Cấu hình | Test acc | Train loss epoch cuối | Thời gian mỗi lần |
| --- | --- | --- | --- |
| Đầy đủ | 0.9853 / 0.9848 | 0.011 | 22 s |
| Bỏ BatchNorm | 0.9839 / 0.9853 | 0.008 | 24 s |
| Bỏ dropout | 0.9861 / 0.9856 | 0.001 | 20 s |
| Bỏ cả hai | 0.9852 / 0.9834 | 0.001 | 20 s |
| Weight decay 0 | 0.9856 / 0.9848 | 0.011 | 21 s |
| lr cố định 2e-3 (không cosine) | 0.9813 / 0.9824 | 0.031 | 17 s |
| SGD momentum 0.9, lr 0.05, cosine | 0.9826 / 0.9829 | 0.027 | 14 s |

Đọc kết quả, đây là điều quan trọng nhất của báo cáo:

- **BatchNorm, dropout, weight decay không tạo khác biệt đo được** ở thiết lập này: mọi chênh lệch dưới 0.2
  điểm, ngang chênh lệch giữa hai seed của cùng cấu hình (đến 0.18 điểm). MLP này trên MNIST chưa overfit đủ
  để regularization có việc làm trong 10 epoch; dropout còn làm train loss cao gấp 10 lần mà test không đổi.
- **Cosine schedule là thứ duy nhất giúp ổn định**: +0.24 và +0.40 điểm ở hai seed, train loss thấp hơn 3 lần. Lr nhỏ
  dần ở cuối cho phép "lắng" vào đáy.
- AdamW hơn SGD momentum khoảng 0.2 điểm, nhưng lr SGD chưa tune; kết luận đúng là "AdamW mặc định đã đủ tốt",
  không phải "AdamW tốt hơn SGD".
- Hai seed không đủ để khẳng định chênh lệch 0.1 điểm. Báo cáo tốt nói rõ điều đó, và nếu muốn khẳng định thì
  chạy 5 seed hoặc dùng McNemar trên cùng tập test.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass, test MNIST ≥ 0.975 trong thời gian cho phép |
| Thiết kế framework | 20 | API nhất quán (forward/backward/parameters/state, train/eval); xử lý đúng weight decay, running stats, tái lập; có gradient check từng layer |
| Thiết lập và tái lập | 10 | Ghi split, siêu tham số, seed, phần cứng, số luồng, thời gian; val tách khỏi test, không chọn gì theo test |
| Ablation | 20 | Ít nhất 4 cấu hình, ≥ 2 seed, cùng ngân sách epoch; bảng có độ phân tán |
| Diễn giải trung thực | 20 | Phân biệt hiệu ứng thật với dao động seed; không kết luận "BatchNorm giúp" khi số liệu không cho thấy; giải thích vì sao |
| Chất lượng portfolio | 15 | Tóm tắt có số ở đầu, hình đường cong có câu đọc, mục "lỗi đã gặp" có triệu chứng và cách phát hiện, có giới hạn và bước tiếp |

Đạt từ 70 điểm. Báo cáo chỉ có bảng số mà không diễn giải, hoặc khẳng định một thành phần "cải thiện" dựa trên
một seed và chênh lệch nhỏ hơn dao động seed, không quá 50 điểm.
