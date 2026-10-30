# Lời giải: recency, tenure và segment khách

Workbook lời giải: `customer_recency.xlsx` cùng thư mục.

## Công thức (hàng 2 của Customers)

| Cột | Công thức |
| --- | --- |
| B | `=MINIFS(Invoices!$B$2:$B$856,Invoices!$C$2:$C$856,A2,Invoices!$G$2:$G$856,"Sale")` |
| C | `=MAXIFS(Invoices!$B$2:$B$856,Invoices!$C$2:$C$856,A2,Invoices!$G$2:$G$856,"Sale")` |
| D | `=COUNTIFS(Invoices!$C$2:$C$856,A2,Invoices!$G$2:$G$856,"Sale")` |
| E | `=SUMIFS(Invoices!$F$2:$F$856,Invoices!$C$2:$C$856,A2,Invoices!$G$2:$G$856,"Sale")` |
| F | `=DATEDIF(B2,C2,"m")` |
| G | `=DATEDIF(C2,$L$1,"d")` |
| H | `=IF(G2<=90,"Active",IF(G2<=180,"At risk","Lost"))` |

Tra cứu: L4 có Data Validation List `Active,At risk,Lost`; `L5 =COUNTIF($H$2:$H$121,L4)`,
`L6 =SUMIFS($E$2:$E$121,$H$2:$H$121,L4)`, `L7 =L6/L5`. Conditional formatting trên `H2:H121`:
Cell value equal to `"Lost"`, nền đỏ nhạt.

## Kết quả

| Segment | Khách | Doanh thu gộp (GBP) | Tỉ trọng doanh thu |
| --- | --- | --- | --- |
| Active (≤ 90 ngày) | 57 | 269 301.02 | 82.2% |
| At risk (91–180 ngày) | 10 | 12 604.77 | 3.8% |
| Lost (> 180 ngày) | 53 | 45 797.92 | 14.0% |
| Tổng | 120 | 327 703.71 | 100% |

39 khách chỉ có 1 đơn, 42 khách có tenure 0 tháng; tenure trung vị 7 tháng, lớn nhất 24; trung vị số
ngày từ lần mua cuối là 139.

## Vì sao như vậy

- **MINIFS/MAXIFS với điều kiện `Sale`**: hoá đơn huỷ có ngày riêng; tính nó vào "lần mua cuối" sẽ làm
  một khách vừa huỷ đơn trông như vừa mua. Doanh thu là gộp (định nghĩa chung), tách riêng đơn huỷ nếu
  CRM cần doanh thu ròng.
- **Ngày báo cáo trong một ô tuyệt đối** `$L$1`, không dùng `TODAY()`: dữ liệu kết thúc 09/12/2011, với
  `TODAY()` mọi khách thành Lost và số đổi mỗi lần mở file. Thiếu `$` thì kéo xuống công thức trỏ sang
  L2, L3 trống và DATEDIF trả `#NUM!` hoặc số vô nghĩa.
- **DATEDIF đếm tháng tròn**: khách 12352 mua lần đầu 12/11/2010, lần cuối 03/11/2011: 11 tháng. 42 khách
  tenure 0 gồm 39 khách một đơn và 3 khách mua nhiều đơn trong chưa đầy một tháng.
- **Bị cắt đầu (left-censoring)**: dữ liệu bắt đầu 01/12/2009, nên tenure tối đa khoảng 24 tháng; khách
  mua từ trước đó bị tính "trẻ" hơn thật. Ghi chú trong README của workbook.
- **Đọc kết quả**: 53/120 khách (44%) là Lost nhưng chỉ mang 14% doanh thu; 57 khách Active mang 82%.
  Với win-back, ưu tiên khách Lost có doanh thu cao (sắp E giảm dần trong nhóm Lost) thay vì gửi cả 53;
  nhóm At risk nhỏ (10 khách, 3.8%) nhưng là nhóm rẻ nhất để giữ. Đây là mẫu 120 khách để học công
  thức; con số tỉ trọng không đại diện cho toàn bộ khách.
- **Data validation và conditional formatting** làm bảng an toàn cho người khác dùng: COUNTIF không phân
  biệt hoa thường (`At Risk` vẫn đếm được 10) nhưng `At-risk` hay `At risk ` (thừa dấu cách) trả 0 im
  lặng; dropdown loại hẳn loại lỗi này.

## Đáp án trắc nghiệm

- `lost-revenue` (c) **khoảng 14%**. 44% là tỉ lệ **khách** Lost, 82% là doanh thu Active.
- `tenure-zero` (a) **42**.
- `datedif-month` (d) **11**: ngày 3 chưa tới ngày 12 nên tháng thứ 12 chưa tròn; 356 là số ngày.
- `report-date` (b).
- `left-censor` (c).
- `validation-why` (d) **10**: COUNTIF không phân biệt hoa thường. Dropdown vẫn cần cho các lỗi gõ khác
  (gạch nối, dấu cách thừa, sai chính tả).
