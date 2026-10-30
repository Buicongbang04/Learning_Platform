# Lời giải: Simpson's paradox Berkeley 1973 và funnel Olist

## Cách làm

1. **`admit_rate`**: `groupby(by)[["applied", "admitted"]].sum()` rồi chia. Cộng số đếm trước rồi mới chia:
   trung bình các tỉ lệ sẽ cho khoa 25 hồ sơ cùng trọng lượng với khoa 900 hồ sơ.
2. **`simpson_flip`**: tỉ lệ gộp theo giới; tỉ lệ theo khoa `unstack("gender")`; trọng số chung là tổng hồ
   sơ mỗi khoa; tỉ lệ khử cơ cấu = trung bình có trọng số. Đảo chiều khi `np.sign` của hai hiệu khác nhau
   và đều khác 0. Đây là **chuẩn hoá trực tiếp** (direct standardization), cách dịch tễ học so tỉ lệ tử
   vong giữa hai dân số có cơ cấu tuổi khác nhau.
3. **`order_funnel`**: `orders[cols].notna().sum()` rồi đặt index tên bước. Đếm độc lập, không yêu cầu
   đơn đi qua mọi bước trước: dữ liệu thật có 14 đơn có mốc giao tới khách nhưng thiếu mốc duyệt thanh
   toán, nên funnel "lồng nhau" và funnel đếm độc lập lệch nhau vài chục đơn.
4. **`step_conversion`**: `funnel / funnel.shift(1)`, bước đầu `fillna(1.0)`.

## Số liệu Berkeley và nguồn

P. J. Bickel, E. A. Hammel, J. W. O'Connell (1975), "Sex Bias in Graduate Admissions: Data from Berkeley",
*Science* 187 (4175): 398-404. Sáu khoa lớn nhất, cùng số với `datasets::UCBAdmissions` trong R
(Admitted/Rejected × Male/Female × Dept A-F; nộp = nhận + từ chối):

| Khoa | Nam nộp | Nam nhận | Nữ nộp | Nữ nhận | % nam | % nữ | % cả khoa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 825 | 512 | 108 | 89 | 62.1 | 82.4 | 64.4 |
| B | 560 | 353 | 25 | 17 | 63.0 | 68.0 | 63.2 |
| C | 325 | 120 | 593 | 202 | 36.9 | 34.1 | 35.1 |
| D | 417 | 138 | 375 | 131 | 33.1 | 34.9 | 34.0 |
| E | 191 | 53 | 393 | 94 | 27.7 | 23.9 | 25.2 |
| F | 373 | 22 | 341 | 24 | 5.9 | 7.0 | 6.4 |
| Tổng | 2 691 | 1 198 | 1 835 | 557 | **44.5** | **30.4** | |

- Nữ cao hơn nam ở **4/6 khoa** (A, B, D, F); nam cao hơn ở C và E, chênh dưới 4 điểm.
- **Cơ chế**: 51.5% hồ sơ của nam nộp vào A và B (tỉ lệ nhận trên 63%), trong khi chỉ **7.2%** hồ sơ của nữ
  vào hai khoa này; phần lớn hồ sơ nữ ở C-F, nơi tỉ lệ nhận 6-35%. Khoa là biến gây nhiễu: nó liên quan
  tới cả giới (nộp vào đâu) lẫn kết quả (khoa khó hay dễ).
- **Khử cơ cấu khoa**: nam 38.7%, nữ **43.0%**. Hiệu đổi dấu từ +14.2 điểm (gộp, nam cao hơn) thành −4.3
  điểm (khử cơ cấu, nữ cao hơn): `simpson_flip(BERKELEY) = True`.
- **Giới hạn**: phân tầng theo khoa chỉ loại nhiễu do khoa. Nó không trả lời vì sao nữ nộp vào khoa khó
  (định hướng, rào cản ở bậc trước), hay hồ sơ có tương đương không. Bickel et al. kết luận đúng mực: không
  thấy thiên vị ở cấp khoa, chênh lệch gộp đến từ nơi ứng viên nộp hồ sơ.

## Funnel Olist

| Bước | Đơn | So với đầu | So với bước trước | Mất ở bước này |
| --- | --- | --- | --- | --- |
| purchased | 99 441 | 100% | | |
| approved | 99 281 | 99.84% | 99.84% | 160 |
| carrier | 97 658 | 98.21% | **98.37%** | **1 623** |
| delivered | 96 476 | **97.02%** | 98.79% | 1 182 |

- Bước **approved → carrier** mất nhiều đơn nhất cả theo số tuyệt đối lẫn theo tỉ lệ: đơn đã thanh toán
  nhưng người bán không giao cho hãng vận chuyển (hết hàng, huỷ).
- Đơn chưa có mốc giao tới khách (2 965): `shipped` 1 107 (phần lớn là đang trên đường hoặc thất lạc),
  `canceled` 619, `unavailable` 609, `invoiced` 314, `processing` 301, còn lại vài đơn. Funnel gộp trộn
  "mất thật" với "chưa xong".
- **Kỳ dở dang**: dữ liệu dừng 17/10/2018; đơn mua tháng 9-10/2018 (20 đơn) chưa đơn nào giao xong, còn
  tháng 5-8/2018 đã giao 97.5-98.8%. Funnel theo tháng phải chỉ tính tháng mua đã đủ thời gian giao (ví dụ
  cách mốc cuối dữ liệu ít nhất 60 ngày, dài hơn hầu hết thời gian giao hứa hẹn).
- **Headline cho PM**: "97% đơn tới tay khách; 1 623 đơn (1.6%) dừng giữa thanh toán và bàn giao vận
  chuyển, bước rò rỉ lớn nhất".

## Đáp án trắc nghiệm

- `depts-women-higher` (c) **4 khoa**.
- `women-mix` (a) **khoảng 7%** (133/1 835 = 7.2%); của nam là 51.5%.
- `adjusted-rates` (b) **nam 38.7%, nữ 43.0%**. (a) là tỉ lệ gộp chưa khử cơ cấu; (c), (d) đảo giá trị.
- `why-flip` (b): cơ cấu nộp hồ sơ. (a) cỡ mẫu nữ 1 835 hồ sơ, không nhỏ; (d) sai định nghĩa: tỉ lệ gộp
  tính theo số hồ sơ, và chính trọng số đó tạo ra nghịch lý.
- `dean-message` (c): không thấy thiên vị ở cấp khoa, chênh lệch gộp do cơ cấu. (a) kết luận từ số gộp;
  (b) nói quá ("chứng minh công bằng") vì phân tầng chỉ loại một biến nhiễu; (d) sai vì 4 526 hồ sơ là đủ.
- `biggest-loss` (b) **approved → carrier**: 1 623 đơn.
- `delivered-share` (c) **97.0%**.
- `recent-orders` (b): chỉ tính các tháng mua đã đủ thời gian giao (cohort đã "chín"), ghi rõ tháng mới là
  chưa đủ dữ liệu. (a) báo động giả; (c) giấu vấn đề vào trung bình; (d) đếm đơn đang đi đường như đã giao.
