---
title: Transfer learning có kiểm chứng trên FashionMNIST
level: advanced
services: []
files:
  - path: starter/transfer.py
    note: 6 hàm TODO
  - path: starter/REPORT.md
    note: Báo cáo thí nghiệm
  - path: tests/test_transfer.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/13-deep-learning/exercises/advanced/01-transfer-learning -q
---

## Mục tiêu

Không tin mặc định "pretrain rồi fine-tune luôn tốt hơn". Tự dựng một thí nghiệm transfer learning có
đối chứng: train từ đầu, linear probe (đóng băng backbone) và fine-tune toàn bộ với learning rate
khác nhau cho từng phần, ở nhiều mức dữ liệu nhãn, rồi kết luận khi nào cách nào đáng dùng.

## Đề bài

1. Trong `starter/transfer.py` viết các công cụ (model là `nn.Sequential`, tầng cuối là head
   `nn.Linear`):
   - `select_classes(X, y, classes)`: lọc mẫu thuộc `classes`, đổi nhãn thành vị trí trong `classes`.
   - `few_shot_indices(y, n_per_class, seed)`: đúng `n_per_class` mẫu mỗi lớp, `ValueError` nếu thiếu.
   - `replace_head(model, n_classes)`, `freeze_backbone(model)`.
   - `make_optimizer(model, head_lr, backbone_lr, weight_decay)`: `AdamW` hai param group, bỏ tham số
     đã đóng băng.
   - `fine_tune(model, X, y, epochs, optimizer, batch_size, seed)`.
2. Thí nghiệm trên FashionMNIST (tải như bài Intermediate 01, dùng 50 000 ảnh train đầu và CNN của
   bài đó):
   - **Nguồn**: lớp 0–4 (T-shirt/top, Trouser, Pullover, Dress, Coat), train CNN 5 lớp.
   - **Đích**: lớp 5–9 (Sandal, Shirt, Sneaker, Bag, Ankle boot) với 10, 50, 200 ảnh nhãn mỗi lớp,
     đánh giá trên 5 000 ảnh test của lớp 5–9.
   - So ba cách: từ đầu; linear probe; fine-tune toàn bộ (lr backbone nhỏ hơn head khoảng 10 lần).
     Mỗi cấu hình ít nhất 3 seed.
3. Viết `starter/REPORT.md` (ít nhất 400 từ): thiết lập, bảng kết quả (trung bình và khoảng
   min–max theo seed), giải thích vì sao kết quả như vậy, khi nào dùng cách nào, và cách áp dụng
   với model pretrain thật (ví dụ ResNet của `torchvision` trên ảnh sản phẩm Olist).

## Tiêu chí đạt

- Các hàm đúng trên dữ liệu nhỏ trong test: lọc và đổi nhãn, few-shot đúng số và tái lập, thay head
  giữ nguyên backbone, đóng băng đúng, param group đúng lr và weight decay, backbone đóng băng không
  đổi sau khi train (kể cả khi có weight decay).
- Trong test, backbone đã học "phát hiện đường thẳng" giúp linear probe với 6 ảnh mỗi lớp đạt trên
  90% trên hai lớp mới (backbone ngẫu nhiên chỉ khoảng 60–80%).
- `REPORT.md` không còn TODO, ít nhất 400 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`freeze_backbone` không đủ để "đóng băng" nếu model có BatchNorm: running mean/var vẫn cập nhật ở
chế độ train. CNN của bài này không có BatchNorm, nhưng hãy nói về điều đó trong báo cáo. Để
`make_optimizer` phân biệt head, so `id(p)` với `id` các tham số của `model[-1]`.

### Gợi ý 2

Đừng chỉ chạy một seed: với 10 ảnh mỗi lớp, chênh lệch giữa hai seed có thể lớn hơn chênh lệch giữa
hai phương pháp. Giữ số bước cập nhật xấp xỉ nhau giữa các mức dữ liệu (nhiều epoch hơn khi ít ảnh),
và đừng chọn epoch theo tập test.
