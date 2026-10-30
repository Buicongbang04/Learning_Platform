# Hướng làm: analysis plan cho "khách quen không quay lại như trước"

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hàm baseline, các con số tham chiếu, một kế hoạch
mẫu rút gọn, các quyết định cần cân nhắc và rubric.

## Hàm `customer_baseline`

Làm sạch theo định nghĩa chung, giữ dòng có `Customer ID`; `month` = tháng của `InvoiceDate`; cờ mới =
`month == groupby("Customer ID")["month"].transform("min")`. `active` = `nunique` khách theo tháng; `new` = `nunique`
khách có cờ mới (reindex, điền 0); `returning = active - new`; doanh thu khách quay lại = tổng doanh thu các dòng không
có cờ mới. Hàm cố ý tính "mới" **trên dữ liệu được đưa vào**: chạy trên một sheet hay hai sheet cho kết quả khác nhau, và
đó là điểm của bài.

## Con số tham chiếu

| Đại lượng | Một sheet (2010-2011) | Hai sheet ghép (bỏ trùng 01-09/12/2010) |
| --- | --- | --- |
| Khách mới tháng 12/2010 | 885 (100%, do cắt đầu) | 76 |
| Khách mới tháng 1/2011 | 417 | 71 |
| Khách mới tháng 9 / 10 / 11 năm 2011 | 299 / 358 / 323 | 189 / 221 / 191 |
| Khách mới tháng 9 / 10 / 11 năm 2010 | (không có) | 243 / 377 / 325 |
| Khách hoạt động tháng 11/2010 / 11/2011 | (không có) / 1 664 | 1 607 / 1 664 |
| Phần doanh thu từ khách quay lại, tháng 11/2011 | 88.2% | 93.0% |

Tỉ lệ khách hoạt động trong tháng m có mua lại trong 3 tháng sau (hai sheet ghép), cùng tháng hai năm:

| Tháng | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | 69.4% | 69.7% | 64.1% | 65.4% | 63.7% | 66.4% | 72.7% | 74.1% |
| 2011 | 64.5% | 66.5% | 64.1% | 68.0% | 65.9% | 67.9% | 72.3% | 75.0% |

Đọc: tỉ lệ mua lại năm 2011 **không thấp hơn có hệ thống** (thấp hơn ở tháng 1–2, cao hơn ở tháng 4–6, gần bằng ở tháng
3, 7, 8). Trong khi đó số **khách mới** mùa thu 2011 thấp hơn mùa thu 2010 rõ rệt (191 so với 325 ở tháng 11). Một kế
hoạch tốt không biết trước kết quả này, nhưng phải có giả thuyết "thu hút giảm, không phải giữ chân giảm" và có cách
kiểm nó. Số liệu trên dùng để chấm phần "Giả thuyết" và "Phương pháp" có hướng đúng không, không để chép vào kế hoạch.

## Kế hoạch mẫu (rút gọn)

- **Bối cảnh và quyết định**: quyết định ngân sách giữ chân khách 2012. "Có" nếu tỉ lệ mua lại trong 3 tháng năm 2011
  thấp hơn cùng tháng 2010 ít nhất 3 điểm % ở đa số tháng; nếu không mà khách mới giảm, ngân sách nên sang thu hút.
- **Câu hỏi đóng khung**: "Năm 2011, tỉ lệ khách hoạt động trong tháng có mua lại trong 3 tháng sau có thấp hơn cùng
  tháng 2010 không, ở khách sỉ và khách lẻ, để quyết định ngân sách giữ chân khách 2012?"
- **Câu hỏi làm rõ**: "khách quen" là ai (từ 2 đơn? khách sỉ?); cảm giác đến từ báo cáo hay khách cụ thể nào; chương
  trình dự kiến nhắm ai, chi phí bao nhiêu (để biết mức thay đổi nào đáng đầu tư); hạn khi nào.
- **Giả thuyết**: (1) cách đo: một sheet làm khách cũ thành mới, tháng 12/2011 chưa đủ; (2) giữ chân giảm thật; (3) thu
  hút giảm chứ không phải giữ chân; (4) chỉ một phân khúc giảm (quốc gia, khách sỉ lớn); (5) khách vẫn quay lại nhưng
  mua ít hơn (tần suất, AOV).
- **Metric**: tỉ lệ mua lại 3 tháng; khách mới theo dữ liệu từ 12/2009; retention cohort tháng k theo định nghĩa chung
  để đối chiếu.
- **Dữ liệu và giới hạn**: con số baseline ở trên; cắt đầu 12/2009; tháng 12/2011 chưa đủ; 16.5% doanh thu không mã;
  không có chi phí, chưa tính lợi nhuận.
- **Phương pháp**: ghép hai sheet và kiểm trùng; tỉ lệ mua lại cùng tháng; khách mới cùng tháng; tách phân khúc; metric
  tree cho khách quay lại.
- **Đầu ra**: kết quả sơ bộ sau 2 ngày, memo một trang sau 1 tuần. **Ngoài phạm vi**: model churn, thiết kế chương
  trình, đo hiệu quả chương trình (cần thí nghiệm).

## Các quyết định cần cân nhắc

- **Đóng khung theo quyết định, không theo cảm giác**: câu hỏi phải nói kết quả nào dẫn tới "có", kết quả nào dẫn tới
  "không" trước khi nhìn số.
- **Metric công bằng giữa hai năm**: "phần khách quay lại trong tháng" tăng dần chỉ vì dữ liệu cắt đầu; dùng cửa sổ cố
  định (mua lại trong 3 tháng) và so cùng tháng.
- **Giả thuyết đối lập**: ít khách mới tạo cảm giác "khách quen ít hơn" cho đội sales giống hệt churn tăng, nhưng dẫn
  tới quyết định ngược lại.
- **Phạm vi**: một trang, vài ngày; nói rõ thứ sẽ không làm để CEO không chờ một model churn.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Quyết định và tiêu chí ra quyết định | 15 | Nêu quyết định ngân sách và ngưỡng kết quả dẫn tới "có"/"không" |
| Câu hỏi đóng khung | 15 | Một câu có metric, so với gì (cùng kỳ), phạm vi, quyết định |
| Câu hỏi làm rõ | 10 | 3–5 câu, mỗi câu đổi được cách phân tích (định nghĩa khách quen, nguồn cảm giác, chi phí chương trình) |
| Cây giả thuyết | 20 | MECE, có nhánh cách đo/cắt đầu và nhánh "thu hút chứ không phải giữ chân", mỗi nhánh có con số kiểm và ngưỡng |
| Metric và dữ liệu | 20 | Định nghĩa đúng định nghĩa chung, nhận ra left-censoring và đề xuất ghép hai sheet bỏ trùng, nêu baseline có số |
| Phương pháp và phạm vi | 15 | Các bước theo thứ tự rẻ trước, kết quả sơ bộ sớm, có mục ngoài phạm vi |
| Văn phong | 5 | Viết cho CEO, ngắn, không thuật ngữ thừa |

Từ 70 điểm trở lên là kế hoạch đủ gửi CEO.

## Sai lầm hay gặp

- Nhảy thẳng vào phân tích (vẽ 20 chart) mà không có câu hỏi đóng khung và tiêu chí quyết định.
- Dùng `returning_share` trên một sheet làm bằng chứng "khách quay lại đang tăng": xu hướng đó chủ yếu do cắt đầu.
- Chỉ có một giả thuyết (churn tăng) và tìm bằng chứng cho nó.
- Đọc cả hai sheet mà không bỏ phần trùng 01–09/12/2010: khách và doanh thu tuần đó bị đếm hai lần.
- Hứa model dự báo churn trong kế hoạch một tuần.
