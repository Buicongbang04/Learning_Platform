# Lời giải: hàm feature dùng chung

`features.py` cạnh tệp này. Ý chính:

- **Hàm vector hoá là nguồn sự thật, `serve_one` chỉ là bộ chuyển đổi.** Một yêu cầu thành DataFrame một dòng rồi đi qua
  cùng mã. Chi phí của DataFrame một dòng (vài trăm micro giây) đáng đổi lấy việc không có hai bản cài đặt; nếu độ trễ thực sự
  không chịu nổi, giữ nguyên hàm vector hoá và gọi nó theo lô nhỏ, đừng viết lại bản riêng.
- **Mã hoá tuần hoàn cho giờ.** Giờ thô 23 và 0 cách nhau 23 đơn vị với model tuyến tính hoặc dựa khoảng cách; `sin/cos` đặt
  chúng cạnh nhau. Test đo khoảng cách 23-0 bằng 0-1.
- **Default được khai báo thành hằng ở một chỗ** (`DEFAULT_DISTANCE`) và có cột `zone_known` để model biết giá trị là thật hay
  điền hộ. Thiếu cột kiểu đó, model học "zone 0" như một địa điểm.
- **Ranh giới ngày/đêm và cuối tuần kiểm ở từng phút biên** (21:59, 22:00, 05:59, 06:00; thứ Sáu 23:59, thứ Bảy 00:00).
  Lỗi `<` và `<=` ở các biên này lệch rất ít mẫu nên không bao giờ lộ ra bằng số tổng hợp.
- **`to_numeric(errors="coerce")` rồi `between`** xử lý `None`, `NaN` và chuỗi hỏng bằng một đường duy nhất.

Lỗi hay gặp: `fillna` trước khi cắt khoảng làm zone 0 trở thành "hợp lệ"; dùng `ts.dt.hour` trên Series rồi gọi lại bằng
`ts.hour` ở đường online (đúng, nhưng là hai mã khác nhau).
