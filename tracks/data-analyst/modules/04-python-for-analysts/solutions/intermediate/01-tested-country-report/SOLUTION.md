# Lời giải: hàm báo cáo theo quốc gia có test bắt được lỗi

## `report.py`

- **`clean_transactions`**: `tx.assign(Invoice=tx["Invoice"].astype(str))` tạo bản sao rồi mới lọc, nên không sửa đầu
  vào. Đọc từ Excel, `Invoice` trộn số (`536365`) và chuỗi (`C536379`); không ép `str` thì `.str.startswith("C")` ra
  `NaN` ở các ô số.
- **`country_summary`**: lọc kỳ **nửa mở** `[start, end)` (`>= start`, `< end`) để hai kỳ liền nhau không đếm trùng
  hoá đơn lúc 00:00 ngày đầu kỳ sau. `nunique` cho `orders` và `customers`; `nunique` bỏ `NaN` nên dòng thiếu mã khách
  không thành một "khách".
- **`compare_periods`**: outer merge hai bảng tổng hợp theo index quốc gia, `validate="one_to_one"` (mỗi kỳ một dòng
  mỗi nước; trùng là lỗi ở bước trước), `indicator=True` để gán `status`. Điền 0 cho doanh thu thiếu, sắp theo doanh
  thu, cắt `top` và gộp `Other`, **rồi** mới tính `change` và `growth` để dòng `Other` có tăng trưởng đúng (tính trên
  tổng, không phải trung bình tăng trưởng các nước).

## `checks_report.py`

Lời giải mẫu có 6 test, mỗi test một định nghĩa:

| Test | Khoá định nghĩa | Bắt lỗi cài sẵn |
| --- | --- | --- |
| `test_aov_is_revenue_per_invoice` (mẫu) | AOV = doanh thu / số hoá đơn | (không lỗi nào; test mẫu cố ý không bắt được) |
| `test_cancellations_and_bad_rows_are_dropped` | Bỏ hoá đơn `C`, giá 0, số lượng âm | Không bỏ hoá đơn huỷ |
| `test_orders_and_customers_are_distinct_counts` | Hoá đơn hai dòng là một đơn; dòng thiếu mã khách không phải khách | Đếm dòng thay vì `nunique` |
| `test_period_is_half_open` | Kỳ `[start, end)` | (phòng lỗi `<= end`) |
| `test_compare_keeps_new_and_lost_countries` | Nước mới/mất, `growth` = kỳ này / kỳ trước − 1 | Inner join; tăng trưởng sai mẫu số |
| `test_top_other_keeps_total` | `Other` giữ đúng tổng | (phòng lỗi bỏ phần còn lại) |

Bốn lỗi cài sẵn và vì sao chúng nguy hiểm ngoài đời:

1. **Không bỏ hoá đơn huỷ**: doanh thu thấp đi (dòng âm cộng vào) hoặc cao lên (đếm cả hoá đơn gốc lẫn số lượng âm),
   số đơn sai. Trên quý 3/2011 Anh có 1 966 628 GBP nếu không làm sạch, thay vì 2 107 119.
2. **`count` thay vì `nunique`**: quý 3/2011 Anh có 110 340 dòng hợp lệ nhưng chỉ 4 192 hoá đơn: "số đơn" sai 26 lần
   mà không báo lỗi gì.
3. **Inner join khi so hai kỳ**: mất đúng những dòng Head of Sales quan tâm nhất (thị trường mới, thị trường mất).
   Quý 3 so với quý 2/2011 mất UAE (mới) và Bahrain, Brazil, USA (mất).
4. **Tăng trưởng chia cho kỳ này**: France 25 → 36 ra +30.6% thay vì +44%; trông hợp lý nên ít ai bắt được.

Đó là lý do bộ chấm dùng **mutation testing** (cài lỗi rồi xem test có đỏ không): độ phủ dòng code 100% không nói gì
nếu test không kiểm đúng con số.

## Con số chính (quý 3/2011 so với quý 2/2011)

| Đại lượng | Giá trị |
| --- | --- |
| Quốc gia có đơn quý 3 / quý 2 | 30 / 32 |
| Doanh thu quý 3 / quý 2 | 2 536 950 / 2 070 085 GBP |
| Anh quý 3 | 2 107 119 GBP, 4 192 hoá đơn, 1 939 khách, 83.1%, +21.4% so với quý 2 |
| EIRE quý 3 | 104 230 GBP, 84 hoá đơn, **3 khách**, +106.6% |
| Netherlands quý 3 | 67 291 GBP, 15 hoá đơn, 2 khách, AOV 4 486 GBP |
| `top=5`, dòng Other | 157 318 GBP (quý 2: 134 445), +17.0% |

Đọc cho Head of Sales: ngoài Anh, ba thị trường lớn nhất (EIRE, Netherlands, Germany) đều là **vài khách sỉ** (EIRE 3
khách, Netherlands 2 khách); "EIRE tăng 107%" là chuyện của 3 khách hàng, nên nói chuyện với account manager trước khi
gọi đó là xu hướng thị trường.

## Lỗi hay gặp

- Viết test bằng cách chạy hàm rồi chép kết quả vào `assert` (test "chụp ảnh"): nó khoá cả lỗi đang có.
- Test chỉ kiểm cột tồn tại và kiểu dữ liệu, không kiểm con số.
- Dữ liệu test quá "đẹp": không có hoá đơn huỷ, không có quốc gia chỉ ở một kỳ, mỗi hoá đơn một dòng. Lỗi chỉ lộ khi dữ
  liệu có trường hợp biên.
- Tính `growth` của dòng `Other` bằng trung bình `growth` các nước.
