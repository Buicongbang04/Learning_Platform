# Lời giải: làm sạch có nhật ký

## Cách làm

- **`normalize`**: chép DataFrame rồi đổi từng cột. Điểm dễ sai: `Customer ID` phải là `Int64` (nullable), vì
  `float` in ra `13085.0` và `int` không chứa được ô thiếu; `StockCode` phải viết hoa trước khi so với
  `FEE_CODES`, nếu không 4 dòng mã `m` (chữ thường) lọt vào doanh thu hàng hoá.
- **`clean_with_log`**: một dict quy tắc, lặp theo `REASONS`, mỗi bước tính mặt nạ trên các dòng **còn lại**,
  ghi số dòng và `Quantity * Price` của dòng bị loại, rồi bỏ chúng. Vì mỗi dòng chỉ bị loại một lần, nhật ký cộng
  lại khớp: tổng thô − tổng `revenue_removed` = doanh thu sạch.
- **`missing_report`**: `df.isna().sum()`, chia cho số dòng, sắp `kind="stable"` để cột bằng nhau giữ thứ tự gốc.

## Nhật ký trên sheet `Year 2009-2010`

| Lý do | Dòng bị loại | Dòng còn lại | Doanh thu bị loại (GBP) |
| --- | --- | --- | --- |
| cancelled | 10 206 | 515 255 | −629 855.37 |
| non_positive_quantity | 2 121 | 513 134 | 0.00 |
| non_positive_price | 1 569 | 511 565 | −136 552.02 |
| fee_code | 2 273 | 509 292 | 466 073.72 |
| exact_duplicate | 6 830 | 502 462 | 34 100.71 |

Đối soát: tổng `Quantity * Price` thô 9 539 484.63 − tổng cột `revenue_removed` (−266 232.96) → doanh thu hàng hoá **9 805 717.59 GBP**. Theo định nghĩa dùng chung (3
quy tắc đầu, 511 565 dòng) doanh thu là 10 305 892.02 GBP; hai bước thêm bớt 500 174.43 GBP (**4.9%**).

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `most-rows` | a. cancelled | 10 206 dòng, gần một nửa số dòng bị loại (22 999) |
| `most-money` | c. fee_code | 466 073.72 GBP dương; `cancelled` và `non_positive_price` loại số âm, `non_positive_quantity` loại dòng giá 0 nên 0 GBP |
| `top-fee` | d. M | 559 dòng nhập tay, 262 618.51 GBP; DOT 116 408.71, POST 49 477.54, AMAZONFEE 20 248.04 |
| `revenue-gap` | b. khoảng 4.9% | (10 305 892.02 − 9 805 717.59) / 10 305 892.02 |
| `missing-customer` | c. khoảng 20.5% | 102 908 / 502 462 |
| `normalize-first` | a | Không chuẩn hoá thì `m` không khớp `M`, và hai dòng chỉ khác khoảng trắng không bị bắt là trùng. `duplicated` chạy được trên cột `object` |
| `keep-missing` | d. Giữ | Doanh thu theo quốc gia không cần mã khách. Bỏ 20% số dòng làm doanh thu thấp sai; điền mã giả tạo ra một "khách" khổng lồ không có thật |
| `duplicate-check` | c | Trùng mọi cột có thể là hành vi thật (quét hai lần cùng món trong một hoá đơn). Hỏi nguồn hoặc so với hệ thống kho trước khi gọi là lỗi; bỏ cả hai dòng làm mất một dòng thật |

## Sai lầm hay gặp

- Áp từng quy tắc trên dữ liệu **gốc** rồi cộng số dòng: các lý do chồng nhau (dòng huỷ có `Quantity < 0`), tổng
  số dòng bị loại vượt số thật và nhật ký không khớp.
- Bỏ mọi dòng có ô thiếu bằng `dropna()`: mất 20% doanh thu vì `Customer ID` thiếu, trong khi báo cáo doanh thu
  không cần cột đó.
- Coi `fee_code` là "dữ liệu bẩn": phí ship là doanh thu thật của công ty, chỉ không phải doanh thu **hàng hoá**.
  Đây là quyết định định nghĩa, ghi trong nhật ký để kế toán chọn, không âm thầm bỏ.
