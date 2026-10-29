# Lời giải: feature thời gian và địa lý

Tệp lời giải: `features.py`.

## Thời gian

- `(a - b) / pd.Timedelta(days=1)` cho số ngày **thực**. `.dt.days` lấy phần nguyên làm tròn xuống,
  nên giao sớm 9.5 giờ thành −1 ngày và giao trễ 15 giờ thành 0 ngày: đúng ở chỗ ranh giới quan trọng
  nhất thì sai.
- `is_late` so nguyên timestamp: `order_estimated_delivery_date` lưu lúc 00:00, nên giao 15:00 đúng
  ngày hẹn là trễ. Đây là định nghĩa chung của track (8.1% đơn giao xong). So theo ngày sẽ ra khoảng
  6.8%; cả hai bảo vệ được, nhưng phải nhất quán giữa các module.
- `NaT > timestamp` là `False`, nên đơn chưa giao có `is_late = 0` nhưng `delay_days = NaN`. Với
  model, giữ NaN để imputer xử lý tường minh, đừng để số 0 giả vờ là "giao đúng hẹn".

Trên Olist thật, trung vị thời gian hứa giao 23.2 ngày, trung vị `delay_days` là −11.9 ngày: Olist
hứa rất xa để phần lớn đơn "giao sớm". Đây là lý do `delivery_days` (thời gian giao tuyệt đối) mạnh
hơn `delay_days` khi đứng một mình: khách thấy chờ 30 ngày là lâu, kể cả khi đúng hẹn.

## Mã hoá vòng tròn

Giờ 23 và giờ 0 cách nhau 1 giờ nhưng cách nhau 23 đơn vị nếu để dạng số. `(sin, cos)` đặt giờ lên
đường tròn đơn vị. Chỉ cần với model tuyến tính, kNN, mạng nơ-ron; cây quyết định tự cắt được khoảng
giờ nên thường không cần. Với Olist, giờ mua gần như không đóng góp gì (bài Advanced 02).

## Địa lý

- Bảng geolocation có khoảng 1 triệu dòng cho 19 015 zip prefix: nhiều điểm mỗi zip. **Trung vị**
  bền với điểm lỗi hơn trung bình.
- 42 dòng có toạ độ ngoài Brazil (có điểm ở châu Âu). Không lọc thì khoảng cách lớn nhất giữa khách
  và seller là 8 678 km; lọc rồi còn 3 398 km, hợp lý với kích thước Brazil.
- Zip prefix phải đọc dạng chuỗi (`dtype=str`) hoặc `zfill(5)`: đọc thành số, `"01037"` thành `1037`
  và mọi join với bảng khác đọc đúng kiểu sẽ trượt im lặng.
- 0.5% đơn không có toạ độ cho khách hoặc seller: để NaN, imputer xử lý trong pipeline.

Trung vị khoảng cách khách–seller là 434 km. Tỉ lệ review xấu tăng từ 10.2% (quartile gần nhất) lên
14.6% (quartile xa nhất): có tín hiệu, nhưng yếu hơn nhiều so với thời gian giao, và phần lớn tác
động có thể đi qua thời gian giao (xa thì giao lâu).

## Sai lầm hay gặp

- Tính khoảng cách Euclid trên độ: 1 độ kinh tuyến ở xích đạo và ở 30° Nam khác nhau khoảng 13%.
- Dùng tên thành phố để join: có dấu, viết hoa khác nhau, trùng tên giữa các bang.
- Tạo feature từ `order_delivered_customer_date` rồi dùng cho model dự đoán **lúc mua**: ở thời điểm
  đó chưa có ngày giao. Feature chỉ hợp lệ với thời điểm dự đoán đã chọn (lúc giao xong).
