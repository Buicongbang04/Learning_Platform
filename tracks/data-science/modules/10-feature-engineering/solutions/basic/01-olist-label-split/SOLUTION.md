# Lời giải: nhãn review xấu và chia theo thời gian

Tệp lời giải: `labels.py`.

## Cách làm

- **Lọc trước, ghép sau.** Đơn giao xong cần cả `order_status == "delivered"` và ngày giao: có 8 đơn
  "delivered" nhưng thiếu ngày giao, không thể tính feature giao hàng cho chúng.
- **Một đơn một review.** 547 đơn có hơn một review. Sắp theo `review_answer_timestamp` (sort ổn định)
  rồi `drop_duplicates(keep="last")`: review khách sửa sau cùng là ý kiến cuối của họ. Nếu ghép thẳng,
  đơn có hai review thành hai dòng: vừa lệch tỉ lệ, vừa có thể nằm ở cả train lẫn test.
- **Inner join** với review: đơn không có review không có nhãn. Đây là một lựa chọn có hệ quả (xem
  dưới).
- **Ranh giới trái đóng, phải mở**, viết bằng hằng `pd.Timestamp` ở đầu tệp để mọi module dùng cùng
  một nguồn sự thật.

## Kết quả trên Olist thật

| Phần | Giai đoạn mua | Số đơn | Review xấu | Giao trễ |
| --- | --- | --- | --- | --- |
| train | 2016-09 → 2017-12 | 43 362 | 12.1% | 6.5% |
| val | 2018-01 → 2018-03 | 20 468 | 18.0% | 14.4% |
| test | 2018-04 → 2018-08 | 31 994 | 10.4% | 5.9% |

Tổng 95 824 đơn, review xấu 12.8%.

**Đọc bảng.** Ba giai đoạn khác nhau rõ: quý 1/2018 giao trễ gấp hơn hai lần các giai đoạn khác và
review xấu cũng cao hơn hẳn. Hệ quả:

- AUC trên validation và trên test sẽ khác nhau dù model không đổi (bài Intermediate 02: 0.80 so với 0.70).
- Một ngưỡng chọn trên validation để "gọi 15% đơn rủi ro nhất" sẽ gọi số đơn khác hẳn trên test.
  Ngưỡng nên được đặt theo tỉ lệ/ngân sách và theo dõi lại sau khi triển khai.
- Không có cách chia nào "sửa" được điều này; chia theo thời gian chỉ làm nó lộ ra, đúng như sẽ xảy
  ra khi chạy thật.

## Sai lầm hay gặp

- Dùng `customer_id` làm khách: mỗi đơn một `customer_id`; khách thật là `customer_unique_id`.
- So sánh ngày dạng chuỗi trong một cột `object` (quên `parse_dates`): so sánh từ điển, đúng tình cờ
  với định dạng ISO nhưng hỏng ngay khi có múi giờ hay định dạng khác.
- Chia ngẫu nhiên "cho cân bằng tỉ lệ nhãn": đúng là ba phần sẽ giống nhau, và chính vì thế mà con số
  đánh giá không còn nói gì về tương lai.
- Quên rằng inner join với review loại các đơn không có review: model chỉ học trên khách chịu viết
  review. Khi dùng thật, model chấm cả những đơn khách sẽ không review; cần nêu giới hạn này.
