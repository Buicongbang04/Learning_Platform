---
title: Điều tra "doanh thu tháng 12 giảm 58%" và viết memo cho Giám đốc kinh doanh
level: advanced
services: []
files:
  - path: starter/investigation.ipynb
    note: 3 hàm TODO + điều tra tự do bằng chart
  - path: starter/MEMO.md
    note: Memo một trang - headline, 3 chart, kết luận, việc cần làm
  - path: tests/test_investigation.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/08-visualization-chart-reading/exercises/advanced/01-revenue-drop-investigation/starter/investigation.ipynb
  - uv run pytest tracks/data-analyst/modules/08-visualization-chart-reading/exercises/advanced/01-revenue-drop-investigation -q
---

## Mục tiêu

Đi hết một vòng điều tra "vì sao metric giảm" như DA làm thật: xác nhận con số có so được không, so sánh
công bằng (cùng số ngày, cùng kỳ năm trước), kiểm ngoại lệ, tách thay đổi theo phân khúc, rồi viết một memo
một trang mà lãnh đạo đọc xong biết phải nói gì và làm gì.

## Đề bài

Giám đốc kinh doanh hỏi: **"Doanh thu tháng 12/2011 giảm mạnh so với tháng 11/2011 (0.64 so với 1.51 triệu
GBP), vì sao?"** Dữ liệu: bộ `online-retail-ii`; sheet `Year 2010-2011` để điều tra, sheet `Year 2009-2010`
chỉ làm lịch sử mua của khách. Bài Intermediate 02 đã cho thấy tháng 12/2011 chỉ có 8 ngày dữ liệu; bài này
đi xa hơn. Mở `starter/investigation.ipynb`:

1. `reversed_lines(tx)`: đánh dấu dòng mua hợp lệ đã bị một dòng huỷ cùng khách, cùng mã hàng, cùng số
   lượng đảo lại (quy tắc ghép đầy đủ trong notebook).
2. `customer_type(tx, history)`: `clean(tx)` thêm cột `customer_type` là `new` (lần mua đầu tiên rơi vào
   cùng tháng), `returning` hoặc `guest` (không có mã khách).
3. `revenue_bridge(rows, a, b, by)`: doanh thu hai kỳ `[start, end)` theo một chiều, cột `a`, `b`, `diff`,
   `share_of_diff`, sắp theo `|diff|` giảm dần.
4. Điều tra bằng chart trong các cell `explore`: chart của stakeholder, độ phủ ngày và giờ cuối có dữ liệu,
   so 1-9/12/2011 với 1-9/11/2011 và 1-9/12/2010, hoá đơn lớn bất thường và phần đã bị huỷ, cầu doanh thu
   theo quốc gia, loại khách, sản phẩm. Chọn 3 chart cho memo, tiêu đề mỗi chart là kết luận có con số.
5. Viết `starter/MEMO.md` theo khung có sẵn (200-600 từ, đủ các mục, dòng đầu là headline có con số).

## Tiêu chí đạt

- `reversed_lines` đúng trên dữ liệu nhỏ: chỉ ghép cùng khách, cùng mã, đủ số lượng, huỷ không trước lúc
  mua, lấy dòng mua muộn nhất; bỏ qua khách vãng lai và dòng không hợp lệ.
- `customer_type` tính lần mua đầu trên cả lịch sử, không tính đơn huỷ là "đã từng mua".
- `revenue_bridge` lấy kỳ nửa mở, điền 0 cho nhóm chỉ có ở một kỳ, `share_of_diff` cộng lại bằng 1.
- Trên bộ thật: 2 860 dòng mua bị huỷ trong năm; 1-9/12/2011 gộp 638 811 GBP, trong đó 169 357 GBP đã bị
  huỷ; sau khi bỏ, 1-9/12/2010 là 436 870 và 1-9/12/2011 là 469 453 GBP; UK đóng góp +20 318 GBP.
- `MEMO.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Trước mỗi chart, viết câu hỏi nó trả lời. Thứ tự hợp lý: con số có so được không (độ phủ) → so với cái gì
(cùng ngày, cùng kỳ năm trước) → con số so sánh có bị một giao dịch quyết định không → thay đổi đến từ đâu.
Đừng tách theo phân khúc trước khi chắc con số tổng đúng: bạn sẽ tách một ảo giác.

### Gợi ý 2

So cùng kỳ năm trước trừ được mùa vụ (đầu tháng 12 là cao điểm đặt quà Giáng sinh), so với 1-9/11 thì
không. Khi một hoá đơn chiếm hơn một phần tư doanh thu cả kỳ, xem nó có bị huỷ ngay sau đó không. Khi xếp
theo sản phẩm, các mã như `POST`, `DOT`, `AMAZONFEE` là phí, không phải hàng hoá.
