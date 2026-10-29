---
title: Phân tích trọn thí nghiệm email Hillstrom và đề xuất chiến lược
level: advanced
services: []
files:
  - path: starter/analysis.ipynb
    note: effects_table + phân tích tự do
  - path: starter/REPORT.md
    note: Báo cáo cho Giám đốc Marketing
  - path: tests/test_effects.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py hillstrom
  - uv run jupyter lab tracks/data-science/modules/03-ab-testing/exercises/advanced/01-hillstrom-email-experiment/starter/analysis.ipynb
  - uv run pytest tracks/data-science/modules/03-ab-testing/exercises/advanced/01-hillstrom-email-experiment -q
---

## Mục tiêu

Làm trọn việc của một DS sau khi thí nghiệm kết thúc: kiểm tra độ tin cậy, ước lượng tác động
nhiều nhánh × nhiều metric với hiệu chỉnh multiple testing, tìm nhóm khách đáng nhắm, quy ra tiền,
và viết khuyến nghị cho lãnh đạo.

## Đề bài

Thí nghiệm email Hillstrom (dữ liệu thật, 64 000 khách, 3 nhánh). Mở `starter/analysis.ipynb`:

1. **Kiểm tra thí nghiệm**: SRM giữa 3 nhánh; balance check các cột hồ sơ khách; phân phối `spend`.
2. **`effects_table(df, control="No E-Mail")`**: DataFrame cột đúng thứ tự
   `arm, metric, diff, ci_low, ci_high, p_value, p_holm`, một dòng cho mỗi (nhánh ≠ control) ×
   (`visit`, `conversion`, `spend`). `p_holm` là adjusted p-value Holm trên cả bảng. Tự chọn phương
   pháp cho từng metric và giải thích lựa chọn.
3. **Heterogeneous effect**: tác động theo `mens`, `womens`, `newbie`, `channel`, `history_segment`.
4. **Quy ra tiền**: email tốn $0.10, biên lợi nhuận 30%. So sánh chiến lược gửi cho tất cả với gửi
   có chọn lọc; ước tính lợi nhuận trên 100 000 khách kèm khoảng không chắc chắn.
5. **`REPORT.md`**: tối đa một trang rưỡi cho Giám đốc Marketing, theo khung có sẵn.

## Tiêu chí đạt

- `effects_table` đúng cấu trúc; CI chứa `diff`; `p_holm ≥ p_value`; phát hiện đúng tác động có
  thật và không báo tác động không có thật trên dữ liệu mô phỏng; hỗ trợ đổi nhóm control.
- Trên dữ liệu thật: email nữ làm visit tăng khoảng 4.5 điểm phần trăm, CI không chứa 0.
- `REPORT.md` không còn TODO, ít nhất 250 từ.
- Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`spend` bằng 0 với hơn 99% khách. Đó là metric "doanh thu trên mỗi khách được random", đúng thứ
kinh doanh cần, và với 21 nghìn khách mỗi nhánh thì Welch t-test vẫn ổn nhờ CLT. Muốn chắc hơn thì
so với bootstrap. Đừng chỉ phân tích trên người đã mua: đó là so sánh hai nhóm **không còn ngẫu
nhiên** (email thay đổi ai là người mua).

### Gợi ý 2

Khi xét segment, so tác động của **cùng một email** giữa các segment (ví dụ email nữ cho khách
`womens = 1` vs `womens = 0`). Để biết chênh lệch giữa hai segment có thật không, kiểm định chính
chênh lệch đó (hoặc hồi quy có biến tương tác `treatment × segment`), không phải so "segment này có
ý nghĩa, segment kia không".
