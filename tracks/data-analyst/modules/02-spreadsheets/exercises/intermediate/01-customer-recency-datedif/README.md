---
title: Recency, tenure và segment khách bằng DATEDIF, MINIFS/MAXIFS, data validation, conditional formatting
level: intermediate
services: []
files:
  - path: starter/customer_recency.xlsx
    note: 7 cột TODO + ô tra cứu L4:L7 + 1 data validation + 1 conditional formatting
  - path: tests/test_customer_recency.py
    note: Không sửa
run:
  - libreoffice --calc tracks/data-analyst/modules/02-spreadsheets/exercises/intermediate/01-customer-recency-datedif/starter/customer_recency.xlsx
  - uv run pytest tracks/data-analyst/modules/02-spreadsheets/exercises/intermediate/01-customer-recency-datedif -q
---

## Mục tiêu

Dựng bảng khách hàng mà team CRM tự dùng được: ngày mua đầu/cuối, số đơn, doanh thu, tenure và
recency bằng DATEDIF, segment bằng IF lồng, ô chọn segment có dropdown và tô màu khách đã mất.

## Đề bài

Team CRM chuẩn bị chiến dịch win-back và hỏi: *"Trong mẫu khách này, bao nhiêu khách đã lâu không
mua, và họ từng đáng bao nhiêu tiền?"*

Workbook `starter/customer_recency.xlsx` (Online Retail II, CC BY 4.0):

- `Invoices`: 855 hoá đơn của 120 khách chọn ngẫu nhiên, gộp **cả hai sheet** (bỏ phần trùng
  01–09/12/2010), mỗi dòng một hoá đơn: `InvoiceTotal` là tổng dòng hợp lệ (đơn bán) hoặc tổng dòng
  huỷ (đơn `Cancel`, số âm); `Type` là `Sale` hoặc `Cancel`; ngày chỉ giữ phần ngày.
- `Customers`: 120 mã khách; ngày báo cáo ở ô `L1` = 10/12/2011 (ngày sau giao dịch cuối của bộ dữ liệu).

Sheet `Customers`, hàng 2 rồi kéo xuống tới 121 (chỉ tính hoá đơn `Sale`):

| Cột | Tên | Yêu cầu |
| --- | --- | --- |
| B | `FirstPurchase` | `MINIFS` ngày theo khách |
| C | `LastPurchase` | `MAXIFS` |
| D | `Orders` | `COUNTIFS` |
| E | `Revenue` | `SUMIFS` của `InvoiceTotal` (doanh thu gộp) |
| F | `TenureMonths` | `DATEDIF(B, C, "m")` |
| G | `DaysSinceLast` | `DATEDIF(C, $L$1, "d")`, ngày báo cáo là tham chiếu tuyệt đối |
| H | `Segment` | `≤ 90` ngày `Active`, `≤ 180` ngày `At risk`, còn lại `Lost` (IF lồng) |

Ngưỡng 90/180 ngày là **ví dụ giả định** của team CRM, không phải chuẩn ngành.

Thêm:

1. Ô `L4`: **Data Validation** dạng List `Active,At risk,Lost` (LibreOffice: Data > Validity; Excel:
   Data > Data Validation), chọn một giá trị. `L5` số khách, `L6` doanh thu, `L7` doanh thu trung bình
   mỗi khách của segment ở L4.
2. **Conditional Formatting** cho `H2:H121`: ô bằng `Lost` tô nền đỏ nhạt.

Lưu `.xlsx` rồi chạy test. Làm thêm phần trắc nghiệm trong app.

## Tiêu chí đạt

- B2:H121 và L5:L7 là công thức đúng họ hàm; G dùng `$L$1`; giá trị khớp tính lại từ sheet Invoices.
- Segment: 57 Active, 10 At risk, 53 Lost. Khách 12352: tenure 11 tháng, 37 ngày từ lần mua cuối.
- L4 có data validation dạng danh sách; L5:L7 đúng với segment đang chọn.
- H2:H121 có conditional formatting bắt giá trị `Lost`.
- Trắc nghiệm trong app: đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

`=MINIFS(Invoices!$B$2:$B$856,Invoices!$C$2:$C$856,A2,Invoices!$G$2:$G$856,"Sale")`. Ô ra số kiểu
`40494` là ngày chưa được định dạng; đổi định dạng ô sang ngày, giá trị không đổi.

### Gợi ý 2

DATEDIF đếm tháng **tròn**: 12/11/2010 → 03/11/2011 là 11 tháng. Segment:
`=IF(G2<=90,"Active",IF(G2<=180,"At risk","Lost"))`. Conditional formatting trong LibreOffice: chọn
H2:H121, Format > Conditional > Condition, "Cell value is" "equal to" `"Lost"`.
