---
title: Take-home 3 giờ mô phỏng - nên cắt 20% mã hàng nào năm 2012?
level: advanced
services: []
files:
  - path: starter/takehome.ipynb
    note: 3 hàm được chấm + phân tích của bạn
  - path: starter/SUBMISSION.md
    note: Bài nộp - tóm tắt, giả định, kết quả, khuyến nghị, nhật ký thời gian
  - path: tests/test_takehome.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/advanced/01-take-home-3h/starter/takehome.ipynb
  - uv run pytest tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/advanced/01-take-home-3h -q
---

## Mục tiêu

Làm một take-home đúng điều kiện thật: đề mơ hồ có chủ ý, dữ liệu bẩn, **3 giờ**, người chấm đọc hai phút đầu của bài nộp.
Bài kiểm cả kỹ năng phân tích lẫn những thứ module này dạy: ghi giả định thay vì hỏi mãi, chọn một câu hỏi làm sâu, tóm
tắt cho người ra quyết định trước, nói rõ giới hạn, và tôn trọng time box.

## Đề bài

Đề gửi ứng viên (công ty và người hỏi là **ví dụ giả định**; dữ liệu là thật):

> Chúng tôi là cửa hàng quà tặng bán online ở Anh, khách gồm nhiều cửa hàng bán sỉ. Head of Merchandising muốn **cắt
> khoảng 20% số mã hàng (SKU) trong năm 2012** để giảm tồn kho và chi phí kho, và hỏi: *nên cắt những mã nào, và rủi ro là
> gì?* Dữ liệu đính kèm: giao dịch 01/12/2010 - 09/12/2011 (bộ `online-retail-ii`, sheet `Year 2010-2011`). Bạn có **3 giờ**.
> Nộp một notebook chạy được và một bài viết cho Head of Merchandising. Đề cố ý không nói hết; khi thiếu thông tin, ghi giả
> định và làm tiếp.

Bấm giờ trước khi đọc dữ liệu. Trong `starter/takehome.ipynb`:

1. Ba hàm được chấm trên dữ liệu nhỏ (định nghĩa chi tiết trong notebook):
   - `clean_product_lines(tx)`: dòng hợp lệ theo định nghĩa dùng chung, chỉ mã hàng hoá (5 chữ số + chữ cái tuỳ chọn, sau
     khi bỏ khoảng trắng và viết hoa), thêm `revenue`.
   - `sku_table(sales)`: doanh thu, số lượng, số hoá đơn, số khách theo mã.
   - `cut_impact(sales, cut_skus)`: doanh thu mất trực tiếp, số khách từng mua mã bị cắt, và toàn bộ doanh thu của những
     khách đó.
2. Phân tích của bạn: chọn kỳ, đo phương án ngây thơ (20% mã doanh thu thấp nhất), đề xuất ít nhất một phương án tốt hơn
   có tiêu chí giải thích được, so trên cùng chỉ số, một chart cho người ra quyết định.
3. `starter/SUBMISSION.md` theo khung tám mục.

Tự kiểm phần làm sạch: trên 12 tháng 12/2010-11/2011, có 3 789 mã hàng hoá khác nhau sau chuẩn hoá.

## Tiêu chí đạt

- Ba hàm qua test trên dữ liệu nhỏ: bỏ huỷ, số lượng/giá không dương, mã phí và phiếu quà; chuẩn hoá mã chữ thường và
  khoảng trắng; `Invoice` đọc thành số vẫn thành chuỗi; bảng mã sắp đúng; tác động cắt tính khách thiếu mã đúng cách.
- `SUBMISSION.md` không còn TODO, 400-1200 từ, dòng đầu là headline có con số, đủ tám mục theo thứ tự; tóm tắt tối đa 150
  từ và có ít nhất ba con số; ít nhất ba giả định; nhật ký thời gian có dòng `Tổng thời gian: X giờ` với X ≤ 3.5.
- Notebook chạy được từ đầu tới cuối.
- Nội dung chấm theo rubric 100 điểm trong `SOLUTION.md` (người chấm thật dùng rubric tương tự).

## Gợi ý

### Gợi ý 1

Doanh thu mất trực tiếp khi cắt mã bán chậm gần như luôn nhỏ: đó là định nghĩa của "bán chậm". Câu hỏi rủi ro thật là
**ai** mua những mã đó. Một khách sỉ lớn mua một mã hiếm cùng hàng trăm mã khác có thể chuyển cả đơn sang nhà cung cấp
khác khi mã đó biến mất.

### Gợi ý 2

Trước khi xếp hạng, xem mỗi mã bắt đầu bán từ khi nào: một mã ra mắt tháng 11 có doanh thu cả năm thấp vì mới có một tháng.
Viết tóm tắt cuối cùng nhưng dành cho nó ít nhất 30 phút; phần lớn người chấm quyết định ở đó.
