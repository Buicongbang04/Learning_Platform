---
title: Chính sách liên hệ chủ động đơn có nguy cơ review xấu
level: advanced
services: []
files:
  - path: starter/policy.py
    note: 2 hàm TODO
  - path: starter/DECISION.md
    note: Tài liệu đề xuất cho quản lý
  - path: tests/test_policy.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/11-classic-ml/exercises/advanced/02-olist-contact-policy -q
---

## Mục tiêu

Đi từ model tới **quyết định có ràng buộc**: chọn ngưỡng theo chi phí khi năng lực CSKH có hạn, ước lượng khoản
tiết kiệm kèm độ không chắc chắn, phân tích độ nhạy, và viết đề xuất mà quản lý có thể duyệt. Bài này cung cấp
`capacity_threshold` và `bootstrap_saving` cho M03 của capstone; model capstone dự đoán sớm hơn, lúc giao cho đơn vị vận chuyển.

## Đề bài

Đội CSKH Olist gọi điện cho đơn có nguy cơ review xấu ngay khi giao. Giả định (bạn được đổi, nhưng phải nêu rõ):
một review xấu gây thiệt hại 30 R$, một cuộc gọi tốn 5 R$, cuộc gọi ngăn được review xấu với xác suất s (thử
0.3 và 0.5), CSKH gọi tối đa 100 đơn mỗi tuần.

1. Ma trận chi phí theo s: gọi một đơn sẽ bị review xấu tốn $$5 + (1 - s) \cdot 30$$, gọi đơn không có vấn đề
   tốn 5, bỏ lỡ tốn 30, đơn ổn không gọi tốn 0.
2. `starter/policy.py`:
   - `capacity_threshold(y, p, costs, max_contact_rate)`: ngưỡng tối ưu chi phí với ràng buộc tỉ lệ liên hệ.
   - `bootstrap_saving(y, p, threshold, costs, n_boot, seed, alpha)`: tiết kiệm mỗi đơn so với không gọi ai,
     kèm CI percentile bootstrap.
3. Dựng model trên Olist (bảng và cách chia của bài Intermediate 01; có thể thêm feature, tuning), kiểm tra
   calibration, chọn ngưỡng trên **validation**, đánh giá trên **test**. Notebook tự tạo, không chấm tự động.
4. Viết `starter/DECISION.md` theo khung có sẵn.

## Tiêu chí đạt

- `capacity_threshold` đạt đúng chi phí nhỏ nhất có thể dưới ràng buộc (so với vét cạn), không vượt năng lực,
  trùng với tối ưu không ràng buộc khi năng lực dư, không gọi ai khi năng lực bằng 0.
- `bootstrap_saving`: tiết kiệm đúng trên dữ liệu gốc, CI chứa nó, tái lập với seed, độ rộng khớp sai số chuẩn
  lý thuyết, hẹp lại khi dữ liệu nhiều hơn.
- `DECISION.md` không còn TODO, ít nhất 450 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Tính chi phí và tỉ lệ liên hệ cho mọi ngưỡng ứng viên một lần (sắp p giảm dần, `cumsum`), rồi chọn ngưỡng chi
phí nhỏ nhất trong các ngưỡng thoả `rate <= max_contact_rate`. Bootstrap: tính tiết kiệm của **từng đơn**
(chi phí không gọi trừ chi phí chính sách) một lần, rồi resample chỉ số và lấy trung bình.

### Gợi ý 2

Năng lực tính trên tuần: tập test có khoảng 1 500 đơn mỗi tuần, nên 100 cuộc gọi là khoảng 6.7%. Nhưng ngưỡng
chọn trên validation cho 6.7% ở validation có thể chỉ cho 1–2% ở test nếu tỉ lệ rủi ro đổi. So sánh "ngưỡng cố
định" với "gọi top 100 điểm cao nhất mỗi tuần".
