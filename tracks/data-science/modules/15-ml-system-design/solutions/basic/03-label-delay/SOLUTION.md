# Lời giải: label delay

## Cách làm

`known_at` chọn giữa hai cột theo từng dòng bằng `where`: đơn trễ được biết **ngay khi qua ngày hẹn**,
không phải lúc giao. Hệ quả: hai loại nhãn về ở hai tốc độ khác nhau. Trên Olist, đơn tới tay khách sau
trung vị 10.2 ngày kể từ lúc mua, còn ngày hẹn (thời điểm biết một đơn trễ) có trung vị 23.2 ngày sau
khi mua. Nhãn âm về trước, nhãn dương về sau.

`observed_late_rate` tính tỉ lệ trên **những đơn đã có nhãn**, đúng như một dashboard ngây thơ làm.

## Đọc kết quả trên Olist

| Nhìn vào ngày | Đơn mua 02/2018 đã có nhãn | Tỉ lệ trễ nhìn thấy |
| --- | --- | --- |
| 2018-03-01 | 47% | 1.4% |
| 2018-03-15 | 86% | 8.9% |
| 2018-03-29 | 100% | 15.8% |
| Sự thật | | 16.0% |

Tháng 02–03/2018 là khủng hoảng vận chuyển lớn nhất trong dữ liệu, và dashboard ngây thơ báo tỉ lệ trễ
thấp kỷ lục đúng lúc đó. 95% nhãn có trong khoảng 25.4 ngày sau khi mua (`maturity_days(lab, 0.95)`).

Cách dùng trong monitoring:

- Metric chất lượng (precision@k, recall, tỉ lệ trễ) chỉ tính trên cohort **đã chín**, và mốc chín
  phải tính theo nhãn **trễ** (`maturity_days(lab[lab.late], 0.95)` ≈ 34.2 ngày), không theo mọi nhãn
  (25.4 ngày). Mốc 30 ngày chỉ có 85.9% nhãn trễ: tỉ lệ trễ vẫn bị báo thấp. Dùng 35 ngày.
- Song song theo dõi chỉ báo có ngay: số đơn **đã quá hẹn mà chưa giao** (đây là ca trễ biết sớm nhất),
  phân phối điểm model, số cảnh báo mỗi ngày.
- Ghi rõ trên dashboard "số liệu tới cohort ngày X".

## Bẫy thường gặp

- Lọc "chỉ đơn đã giao" khi tính tỉ lệ trễ của tuần gần nhất: đơn trễ chính là đơn chưa giao.
- Retrain hằng ngày trên dữ liệu gồm cả cohort chưa chín: model học tỉ lệ dương thấp hơn thật.
- Nhớ rằng bảng này chỉ gồm đơn **cuối cùng** đã giao xong; trong vận hành thật, đơn huỷ hoặc thất lạc
  cũng phải có nhãn của riêng nó.
