---
title: Mini framework numpy đạt 97.5% trên MNIST (portfolio)
level: advanced
services: []
files:
  - path: starter/framework.ipynb
    note: 16 lớp/hàm TODO, API gợi ý được đổi
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_framework.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py mnist
  - uv run jupyter lab tracks/ai-engineer/modules/01-nn-from-scratch/exercises/advanced/01-numpy-framework-mnist/starter/framework.ipynb
  - uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/advanced/01-numpy-framework-mnist -q
---

## Mục tiêu

Gom mọi mảnh của module (layer, backprop, khởi tạo, optimizer, BatchNorm, dropout) thành một framework nhỏ kiểu
PyTorch, tự thiết kế API, train MLP tới **≥ 97.5% test accuracy** trên MNIST, rồi chứng minh bằng ablation có
kiểm soát cái gì thật sự giúp. Đây là một bài portfolio: code và `REPORT.md` phải đọc được với người chưa
từng mở notebook.

## Đề bài

**Phần cứng:** CPU · ~360 phút

Thời gian trên là thời gian làm bài (framework, thí nghiệm, báo cáo). Chạy cả notebook: bản tham chiếu mất
khoảng 4 phút với `OMP_NUM_THREADS=4` (model chính 15 epoch 30 giây, ablation 5 cấu hình × 2 seed hơn 3 phút),
framework của bạn có thể chậm hơn.

1. Trong `starter/framework.ipynb` dựng framework bằng numpy, không dùng PyTorch:
   - `Module` (`forward`, `backward`, `parameters`, `state`, `train`/`eval`) và `Sequential`.
   - `Linear` (He init), `ReLU`, `BatchNorm1d`, `Dropout`, `SoftmaxCrossEntropy`.
   - `AdamW` (weight decay chỉ cho tham số được đánh dấu), `SGDMomentum` để so, `cosine_lr` có warmup.
   - `EarlyStopping` chụp và nạp lại trạng thái tốt nhất, **kể cả running stats** của BatchNorm.

   API trong notebook là gợi ý, bạn được đổi. Test chỉ gọi ba hàm, tên và thứ tự tham số giữ nguyên, được
   thêm tham số keyword có mặc định (`**options`) để chạy ablation:
   - `build_model(seed: int)`: model 784 → 10 logits, mọi số ngẫu nhiên (init, dropout) lấy từ `seed`.
   - `fit(model, X, y, X_val, y_val, epochs: int) -> dict[str, list[float]]`: history `train_loss` (trung
     bình theo mẫu) và `val_acc`, mỗi phần tử một epoch đã chạy; có early stopping; khi trả về, model mang
     trọng số của epoch val tốt nhất và ở chế độ eval; cùng seed cho cùng history.
   - `evaluate(model, X, y) -> float`: accuracy ở chế độ eval, không đổi trạng thái model.
2. Chạy các cell `explore`: gradient check cả mạng nhỏ, train model chính (val = 10 000 ảnh cuối của tập
   train, test chỉ dùng để báo cáo), lưu `curves.png`, và bảng ablation: bỏ BatchNorm, bỏ dropout, lr cố định
   thay cosine, SGD momentum thay AdamW, mỗi cấu hình ít nhất 2 seed.
3. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` portfolio tốt** đọc trong 5 phút mà không cần mở code:

- Mở bằng **tóm tắt có số**: "framework numpy 600 dòng, MLP 784-512-256-10, test 98.4%, 25 giây trên CPU
  laptop", không mở bằng lịch sử deep learning.
- **Kiến trúc** là sơ đồ hoặc bảng lớp, kèm 2–3 quyết định thiết kế và lý do (vì sao `Param` có cờ decay, vì
  sao `state()` khác `parameters()`), giống một design doc ngắn.
- **Thiết lập tái lập được**: split, siêu tham số, seed, phần cứng, số luồng BLAS, thời gian chạy.
- **Đường cong** có hình và câu đọc hình (epoch tốt nhất, có overfit không, early stopping dừng ở đâu).
- **Ablation trung thực**: bảng có độ phân tán theo seed; nói thẳng chênh lệch nào nằm trong dao động seed.
  "BatchNorm không giúp gì đáng kể ở đây" là một kết quả tốt nếu số liệu nói vậy.
- **Lỗi đã gặp** là phần nhà tuyển dụng đọc kỹ nhất: triệu chứng, cách khoanh vùng (gradient check, overfit
  một batch, so PyTorch), cách sửa. Nó cho thấy bạn debug được model, không chỉ chạy được model.
- **Giới hạn**: MLP không phải CNN, MNIST đã bão hoà, framework thiếu gì so với PyTorch.

## Tiêu chí đạt

- Trên dữ liệu sinh (10 cụm 784 chiều): history đúng định dạng (cùng độ dài, 1 tới `epochs` phần tử, số thực
  hữu hạn, val accuracy trong [0, 1]), loss giảm, val accuracy ≥ 0.8 sau 4 epoch; cùng seed cho cùng history.
- `evaluate` trả số trong [0, 1], gọi hai lần cho cùng kết quả, chia dữ liệu thành nhóm 5 ảnh vẫn ra cùng số
  ảnh đúng (eval mode thật sự).
- Trên dữ liệu "bẫy thuộc lòng" (40% nhãn train sai, val tụt nếu train lâu), `evaluate` trên val sau `fit` bằng
  đúng val accuracy cao nhất trong history.
- MNIST thật: `fit(build_model(0), 50 000 ảnh train đầu, 10 000 ảnh còn lại làm val, epochs=10)` cho test
  accuracy ≥ 0.975, dưới 4 phút (bản tham chiếu: 0.985, khoảng 25 giây).
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng và hình đường cong (tệp hình tồn tại).
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Cho mỗi layer tự ghi gradient vào `Param.grad` của nó trong `backward`, rồi optimizer chỉ cần duyệt
`model.parameters()`. Đánh dấu `decay=False` cho bias, `gamma`, `beta` ngay lúc tạo. Kiểm từng layer bằng
gradient check (float64) trước khi ghép, và overfit một batch 32 ảnh trước khi train cả tập.

### Gợi ý 2

`EarlyStopping` chụp bằng `[a.copy() for a in model.state()]` và nạp lại bằng `a[...] = s` (ghi vào chính mảng
cũ, không gán tên mới). Cosine schedule tính theo **bước**: tổng số bước là `epochs * ceil(N / batch_size)`.
Bản tham chiếu dùng 784-512-256-10, BatchNorm, dropout 0.2, AdamW lr 2e-3 weight decay 0.05, batch 128,
patience 3.
