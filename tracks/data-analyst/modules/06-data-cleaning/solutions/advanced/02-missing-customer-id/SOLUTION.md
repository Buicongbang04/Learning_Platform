# Hướng làm: một phần tư số dòng không có mã khách

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hai hàm, bằng chứng tham chiếu trên bộ thật, các
quyết định cần cân nhắc và rubric chấm memo.

## Hai hàm

- **`missing_profile`**: `groupby(by)[col]`, `size()` cho `rows`, `isna().sum()` theo nhóm cho `missing` (ép `int64`),
  `missing_rate = missing / rows`; `sort_index()` rồi `sort_values("rows", ascending=False, kind="stable")` để bằng
  nhau thì khoá tăng dần.
- **`invoice_summary`**: thêm cột `revenue` và cờ `isna()`, sắp theo `InvoiceDate` (ổn định), `groupby("Invoice")`:
  `size`, `sum`, `all`, `any & ~all`, `Country.first()`, `InvoiceDate.min().dt.hour`; `sort_index()`.

## Bằng chứng tham chiếu (530 105 dòng hợp lệ)

| Hạng mục | Con số |
| --- | --- |
| Dòng thiếu mã | 132 220 (24.9%), doanh thu 1 755 276.64 GBP (16.5%) |
| Hoá đơn | 19 960; thiếu mã 1 428 (7.2%); lẫn lộn **0** |
| Quốc gia | UK 27.0% dòng thiếu; 98.9% dòng thiếu mã ở UK (UK chiếm 91.5% số dòng); Đức, Tây Ban Nha, Hà Lan 0%; EIRE 8.3% |
| Giờ (tỉ lệ dòng thiếu) | 8h 1.2%, 9h 34.9%, 12h 6.6%, 15h 40.5%, 16h 54.9%, 17h 52.6%, 18h 62.0% |
| Tháng | 16.4% (10/2011) tới 38.1% (01/2011) |
| Hoá đơn thiếu mã so với có mã | trung vị 36 so với 15 dòng; giá trị trung vị 465.10 so với 303.04 GBP, trung bình 1 229 so với 481 (Mann-Whitney p = 6e-5) |
| Dòng thiếu mã so với có mã | trung vị Quantity 1 so với 6; trung vị Price 3.29 so với 1.95 |
| Bỏ hết dòng thiếu mã | doanh thu −16.5%; AOV 534.40 → 480.87 |
| Điền một mã "GUEST" | "GUEST" 1 755 277 GBP, gấp 6.3 lần khách lớn nhất thật (14646, 280 206 GBP); 1 428 hoá đơn; số khách 4 338 → 4 339 |
| Khách có mã | 4 338 khách; 65.6% có từ 2 hoá đơn |

Câu chuyện: thiếu mã là thuộc tính của **hoá đơn** và tập trung vào một kiểu hoá đơn (UK, buổi chiều, nhiều món, mỗi món
1 cái, giá đơn vị cao hơn) giống một kênh bán khác. Không MCAR. Với doanh thu: giữ. Với chỉ số khách: tính trên khách có
mã, nói rõ phạm vi, không điền.

Headline mẫu: **"Giữ 1.76 triệu GBP không có mã khách trong doanh thu; chỉ số khách tính trên 4 338 khách có mã, không
điền mã"**.

## Các quyết định cần cân nhắc

- **Cơ chế theo chỉ số**: với doanh thu, thiếu mã không quan trọng (không cần biết ai mua). Với tỉ lệ quay lại, những
  người không mã có thể quay lại hay không ta không biết: không suy được từ khách có mã (MNAR cho câu hỏi đó).
- **MAR có điều kiện**: nếu có cột kênh bán, có thể thiếu chỉ phụ thuộc kênh (MAR). Đề xuất lấy cột đó thay vì đoán.
- **Điền (impute)**: mã chung tạo "khách" khổng lồ; mã khách gần nhất (cùng giờ, cùng quốc gia) bịa ra quan hệ khách
  hàng không có thật. Impute có ý nghĩa cho biến số dùng trong model, không cho một khoá định danh.
- **Bỏ (drop)**: đúng cho chỉ số khách nếu nói rõ phạm vi; sai cho doanh thu và AOV toàn công ty.
- **Kiểm định**: với 19 960 hoá đơn, p-value nhỏ là chắc chắn; điều đáng báo là độ lớn khác biệt (36 so với 15 dòng).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Mức thiếu | 10 | Báo đúng ba con số: % dòng, % doanh thu, % hoá đơn; phát hiện không có hoá đơn lẫn lộn |
| Bằng chứng cơ chế | 25 | Ít nhất ba chiều (quốc gia, giờ, kiểu hoá đơn hoặc tháng) có con số; so hoá đơn thiếu mã với có mã |
| Gọi tên cơ chế | 15 | Bác MCAR có lý do; phân biệt MAR theo kênh và giới hạn MNAR cho chỉ số khách |
| Ảnh hưởng tới chỉ số | 20 | Đo ảnh hưởng của bỏ và điền lên ít nhất ba chỉ số (doanh thu, AOV, khách giá trị cao hoặc quay lại) |
| Khuyến nghị | 20 | Cách tính khác nhau cho chỉ số khác nhau; không điền mã định danh; việc cần làm với nguồn có người và thời điểm |
| Viết cho người đọc | 10 | Headline trả lời thẳng; người đọc không cần biết pandas; giới hạn cụ thể |

Từ 70 điểm trở lên là memo gửi được cho Head of CRM.

## Sai lầm hay gặp

- `dropna()` toàn bảng trước khi làm mọi báo cáo: doanh thu quý thấp đi 16.5%, AOV sai.
- Gọi thiếu là MCAR vì "tỉ lệ thiếu ổn định theo tháng": quên xem theo quốc gia, giờ, kiểu hoá đơn.
- Điền mã bằng `ffill` theo thời gian: hoá đơn của khách vãng lai bị gán cho khách vừa mua trước đó.
- Kết luận "khách không mã chi tiêu nhiều hơn nên là khách VIP": không biết đó là bao nhiêu người.
