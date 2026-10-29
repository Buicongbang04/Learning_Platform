---
title: Memo một trang cho stakeholder
level: advanced
services: []
files:
  - path: starter/sizing.py
    note: 4 hàm TODO
  - path: starter/MEMO.md
    note: Memo tối đa một trang
  - path: tests/test_sizing.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/15-ml-system-design/exercises/advanced/02-stakeholder-one-pager -q
---

## Mục tiêu

Biến toàn bộ phân tích của module thành một trang mà COO đọc trong ba phút và ra được quyết định: khuyến
nghị trước, con số theo kịch bản, giả định nào quyết định kết quả, và điều chưa biết được nói thẳng.

## Đề bài

1. Trong `starter/sizing.py`:
   - `weekly_value(flagged_per_week, precision, effect, loss_event, cost_action)`.
   - `tornado(fn, base, ranges)`: độ nhạy của giá trị theo từng giả định, sắp theo độ lớn.
   - `scenarios(fn, base, ranges)`: bi quan / cơ sở / lạc quan.
   - `break_even(fn, base, param, lo, hi)`: giả định phải lớn / nhỏ cỡ nào để hoà vốn.
2. Chạy với giả định cơ sở của module: 70 cảnh báo mỗi tuần, precision 0.391 (top 5% lúc giao vận
   chuyển), Δ = 0.15, V = 30 R$, tin nhắn 0.5 R$. Tự chọn khoảng cho từng giả định và **ghi lý do**.
3. Viết `starter/MEMO.md` (250–700 từ) gửi COO và trưởng nhóm CSKH. Mục đầu tiên là "Khuyến nghị".

## Tiêu chí đạt

- Bốn hàm đúng trên ví dụ tính tay; tornado sắp đúng; `break_even` báo lỗi khi không có nghiệm.
- Với khoảng giả định trong test, `loss_event` là giả định nhạy nhất và kịch bản bi quan lỗ.
- `MEMO.md` không còn TODO, 250–700 từ, mục đầu là "Khuyến nghị", có con số R$.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`fn(**{**base, param: value})` gọi hàm với một tham số đổi, các tham số khác giữ ở base. Kịch bản bi
quan: với mỗi tham số, lấy cận nào cho giá trị thấp hơn khi xét riêng nó.

### Gợi ý 2

Người kinh doanh trả lời câu "một review xấu có thiệt hơn 8.5 R$ không?" dễ hơn câu "một review xấu
thiệt bao nhiêu?". Viết điểm hoà vốn theo cách đó. Câu đầu của memo phải là một hành động, không phải
một con số AUC.
