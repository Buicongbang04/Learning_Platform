# Lời giải: báo cáo doanh thu Germany và France

Workbook lời giải: `revenue_report.xlsx` cùng thư mục.

## Công thức

Sheet `Data` (hàng 2):

| Cột | Công thức |
| --- | --- |
| I `Valid` | `=IF(AND(LEFT(A2,1)<>"C",D2>0,F2>0),1,0)` |
| J `Revenue` | `=IF(I2=1,D2*F2,0)` |
| K `Month` | `=YEAR(E2)*100+MONTH(E2)` |
| L `OrderStart` | `=IF(AND(A2<>A1,LEFT(A2,1)<>"C"),1,0)` |

Sheet `Report`:

- B3: `=SUMIFS(Data!$J$2:$J$6811,Data!$H$2:$H$6811,$A3,Data!$K$2:$K$6811,B$2)`, kéo ra B3:D4; E3 `=SUM(B3:D3)`; B5 `=SUM(B3:B4)`.
- B8: `=COUNTIFS(Data!$L$2:$L$6811,1,Data!$H$2:$H$6811,$A8,Data!$K$2:$K$6811,B$7)`; tổng như trên.
- B13: `=B3/B8`, kéo ra B13:E15 (dòng 15: `=B5/B10`).
- H2 `=COUNTA(Data!$A$2:$A$6811)`, H3 `=SUM(Data!$I$2:$I$6811)`, H4 `=AVERAGEIF(Data!$I$2:$I$6811,1,Data!$J$2:$J$6811)`,
  H5 `=MAX(Data!$J$2:$J$6811)`, H6 `=MIN(Data!$E$2:$E$6811)`, H7 `=MAX(Data!$E$2:$E$6811)`, H8 `=COUNT(Data!$G$2:$G$6811)`.

## Kết quả

| | 09/2011 | 10/2011 | 11/2011 | 3 tháng |
| --- | --- | --- | --- | --- |
| Doanh thu Germany | 18 091.22 | 31 638.42 | 28 025.02 | 77 754.66 |
| Doanh thu France | 23 428.04 | 33 485.45 | 31 758.71 | 88 672.20 |
| Số đơn Germany / France | 41 / 45 | 58 / 35 | 68 / 64 | 167 / 144 |
| AOV Germany / France | 441.25 / 520.62 | 545.49 / 956.73 | 412.13 / 496.23 | 465.60 / 615.78 |
| AOV cả hai nước | 482.78 | 700.26 | 452.91 | 535.13 |

## Vì sao như vậy

- **Định nghĩa ở một chỗ**: cột Valid là định nghĩa chung của track viết thành công thức. Mọi SUMIFS
  dùng cột Revenue đã lọc, nên đổi định nghĩa (ví dụ trừ đơn huỷ để ra doanh thu ròng) chỉ sửa một cột.
  188 dòng bị loại (đơn huỷ và vài dòng giá 0).
- **Tham chiếu hỗn hợp** `$A3`, `B$2` cho phép một công thức kéo ra cả bảng; viết riêng sáu công thức
  là sáu cơ hội gõ sai.
- **Đếm đơn bằng cờ dòng đầu**: COUNTIFS đếm dòng, không đếm hoá đơn khác nhau. Cờ `A2<>A1` chỉ đúng khi
  các dòng cùng hoá đơn nằm liền nhau; ghi điều kiện này trong README của workbook. Mọi hoá đơn không
  huỷ trong dữ liệu đều có ít nhất một dòng hợp lệ, nên không cần thêm điều kiện Valid.
- **AOV dòng tổng** là 166 426.86 / 311 = 535.13. Trung bình sáu ô AOV ra 562.08, sai vì ô France
  10/2011 chỉ có 35 đơn nhưng được tính ngang ô có 68 đơn.
- **Đọc số**: AOV France 10/2011 = 956.73 GBP vì hoá đơn 573153 (8 895.76 GBP, 61 dòng, khách 12678);
  bỏ hoá đơn này AOV còn 723.23. Một đơn sỉ đủ làm một ô AOV nhảy gấp đôi: báo cáo nên kèm số đơn
  cạnh AOV, và với nhóm nhỏ, nên xem thêm median.
- `COUNT` đếm ô số (Customer ID), `COUNTA` đếm ô không trống (Invoice là text, COUNT sẽ ra 0).

## Đáp án trắc nghiệm

- `excluded-rows` (b) **188** = 6 810 − 6 622. 49 là số dòng không có Customer ID, 311 là số đơn.
- `aov-spike` (b): hoá đơn 573153. (a) sai vì AOV chia theo số đơn, không theo số ngày; (c) sai vì cột
  Valid đã loại đơn huỷ.
- `total-aov` (a). (b) là lỗi trung bình của trung bình.
- `count-vs-counta` (b). (c) ngược: cả hai bỏ qua ô trống thật; khác nhau ở text.
- `orderstart-sort` (b): cờ phụ thuộc thứ tự dòng; sắp lại thì một hoá đơn bị tách, đếm nhiều lần.
- `sumifs-vs-groupby` (b): `pivot_table(index="Country", columns="Month", values="Revenue", aggfunc="sum")`.
