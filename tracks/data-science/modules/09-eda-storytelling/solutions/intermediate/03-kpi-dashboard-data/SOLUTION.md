# Lời giải: dữ liệu cho dashboard KPI

Code: `kpis.py`.

## Cách làm

- **Lưới thời gian đầy đủ trước, số liệu sau.** `pd.period_range` từ tháng đầu tới tháng cuối, rồi
  `reindex` mọi chuỗi vào lưới. Số đếm điền 0, tỉ lệ để NaN: "không có đơn" khác "tỉ lệ trễ 0%".
- **Mẫu số theo từng KPI.** `orders` đếm mọi trạng thái; `late_rate` trên đơn giao xong;
  `bad_review_rate` trên đơn giao xong có review. Mỗi tỉ lệ có mẫu số riêng, và dashboard phải ghi
  rõ.
- **Cờ `complete`** theo một quy tắc định trước (cuối tháng + 30 ngày ≤ thời điểm cắt dữ liệu),
  không theo cảm giác "tháng này trông thấp".
- **Tiêu đề sinh tự động** từ tháng đã chín mới nhất, làm tròn trước khi quyết định "tăng/giảm/không
  đổi" để tiêu đề không nói "tăng 0.0 điểm".

## Kết quả trên Olist thật

- 26 tháng, 2016-11 không có đơn nào: nếu không reindex, line chart nối thẳng 2016-10 sang 2016-12.
- 2018-09 có 16 đơn, 2018-10 có 4 đơn, 0 đơn giao xong: hai tháng `complete = False`. Vẽ thẳng thì
  Olist "sụp đổ" từ 6 512 đơn xuống 16.
- Tháng chín mới nhất là 2018-08. Tiêu đề tự động:
  - `Số đơn tăng 3% (từ 6 292 lên 6 512)`
  - `Tỉ lệ giao trễ tăng từ 4.5% lên 10.4% (+5.9 điểm %)`
  - `Tỉ lệ review xấu giảm từ 9.7% xuống 9.5% (-0.1 điểm %)`

Tháng 8/2018 là một bài học về "chín": theo quy tắc 30 ngày nó đã chín, nhưng tỉ lệ trễ tăng gấp đôi
mà review xấu lại giảm. Đào thêm: 40.5% đơn trễ tháng 8 chỉ trễ trong ngày hẹn (cả bộ dữ liệu:
16.5%), trung vị số ngày trễ 1.77 so với 4.2–6.8 ngày ở tháng 5–7/2018, và review xấu ở đơn trễ tháng 8
chỉ 28.1% (cả bộ: 54.1%). Một phần là **right-censoring**: 47 đơn tháng 8 vẫn ở trạng thái `shipped`
lúc cắt dữ liệu, tức những đơn trễ nặng nhất chưa được tính. Hai KPI đi ngược nhau là tín hiệu để
kiểm tra độ chín và định nghĩa, trước khi viết tiêu đề.

## Sai lầm hay gặp

- Điền 0 cho tỉ lệ của tháng trống: tạo ra một điểm "trễ 0%" giả trên biểu đồ.
- So tháng hiện tại (đang chạy) với tháng trước: tháng hiện tại luôn "giảm".
- `maturity_days` chọn sau khi nhìn số liệu để tháng gần nhất "trông ổn". Quy tắc phải viết trước và
  ghi trên dashboard.
- Tiêu đề đổi số liệu sang phần trăm tương đối cho tỉ lệ ("trễ tăng 131%"): với tỉ lệ, điểm phần
  trăm dễ hiểu và ít gây hoảng hơn; nếu dùng tương đối thì ghi cả hai.
