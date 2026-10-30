# Lời giải: đọc chart doanh thu Online Retail II

## Cách làm

1. **`_clean`**: đổi `Invoice` sang `str`, mặt nạ trên từng dòng (không `C`, `Quantity > 0`, `Price > 0`),
   `tx.loc[mask].assign(revenue=Quantity * Price)` trả bản mới, không sửa `tx`.
2. **`monthly_revenue`**: `set_index("InvoiceDate")["revenue"].resample("MS").sum()`. `resample` tự sinh
   mọi tháng giữa đầu và cuối, tháng trống có tổng 0: một chart xu hướng mà "nhảy cóc" qua tháng trống sẽ
   nối hai điểm xa nhau thành một đường dốc giả.
3. **`country_share`**: tổng theo `Country`, sắp giảm dần, chia cho tổng, cắt `top`, cộng phần còn lại
   thành `Other` đặt cuối (theo nguyên tắc sắp xếp: "Khác" luôn ở cuối, dù lớn hơn vài nước trong top).
4. **`month_coverage`**: `InvoiceDate.dt.normalize()` bỏ trùng là tập ngày có bán; đếm theo tháng rồi
   `asfreq("MS", fill_value=0)` để có cùng index với doanh thu.

## Đọc chart

- **Bước 1, kỳ và độ phủ**: sheet dừng 09/12/2011 nên tháng 12/2011 chỉ có **8 ngày** giao dịch (1-9/12 trừ
  thứ Bảy 3/12). Một tháng đủ có khoảng **26 ngày** vì cửa hàng **không có giao dịch thứ Bảy** nào. Tháng
  12/2010 chỉ có **20 ngày**: nghỉ Giáng sinh, giao dịch cuối là 23/12 và năm mới bắt đầu từ 04/01/2011.
  Tháng 4/2011 có 21 ngày (Phục sinh và các ngày nghỉ lễ cuối tháng 4 ở Anh).
- **Bước 2, hình dạng**: đi ngang khoảng 0.5-0.8 triệu GBP/tháng từ tháng 1 tới tháng 8, rồi tăng mạnh
  tháng 9-11 (mùa đặt hàng quà Giáng sinh của khách sỉ). Tháng 11/2011 là đỉnh, **1.51 triệu GBP**, gấp
  2.9 lần tháng 2/2011 (0.52 triệu, tháng thấp nhất).
- **Bước 3, điểm bất thường**: cú rơi ở tháng 12/2011 là do dữ liệu (8/26 ngày), không phải do kinh doanh.
- **Bước 4, so công bằng**: doanh thu mỗi ngày giao dịch tháng 12/2011 là 79 851 GBP so với 58 058 GBP của
  tháng 11/2011, **tăng khoảng 38%**. Giới hạn: đầu tháng 12 là cao điểm đặt hàng trước Giáng sinh, nên một
  ngày tháng 12 không tương đương một ngày bình quân tháng 11. Nói "tháng 12 đang chạy mạnh", không nói
  "tháng 12 sẽ đạt 2 triệu".
- **Thành phần**: United Kingdom chiếm **84.6%** doanh thu; Netherlands 2.7%, EIRE 2.7%, Germany 2.1%,
  France 2.0%; `Other` (mọi nước còn lại) 5.9%. Pie sẽ là một hình tròn gần như một màu: dùng bar ngang.
- **Headline cho CEO**: "Doanh thu đạt đỉnh 1.51 triệu GBP tháng 11; 8 ngày đầu tháng 12 bán mỗi ngày cao
  hơn tháng 11 khoảng 38%". Điểm tháng 12/2011 vẽ nét đứt, có chú thích "dữ liệu tới 9/12".

## Con số tham chiếu (bộ thật, sheet `Year 2010-2011`)

| Tháng | Doanh thu (GBP) | Ngày giao dịch | GBP / ngày giao dịch |
| --- | --- | --- | --- |
| 12/2010 | 823 746 | 20 | 41 187 |
| 01/2011 | 691 365 | 24 | 28 807 |
| 02/2011 | 523 632 | 24 | 21 818 |
| 03/2011 | 717 639 | 27 | 26 579 |
| 04/2011 | 537 809 | 21 | 25 610 |
| 05/2011 | 770 536 | 25 | 30 821 |
| 06/2011 | 761 740 | 26 | 29 298 |
| 07/2011 | 719 221 | 26 | 27 662 |
| 08/2011 | 759 138 | 26 | 29 198 |
| 09/2011 | 1 058 590 | 26 | 40 715 |
| 10/2011 | 1 154 979 | 26 | 44 422 |
| 11/2011 | 1 509 496 | 26 | 58 058 |
| 12/2011 | 638 811 | 8 | 79 851 |
| Tổng | 10 666 703 | 305 | |

Ngày giao dịch theo thứ: T2 47, T3 52, T4 53, T5 53, T6 50, **T7 0**, CN 50.

## Đáp án trắc nghiệm

- `peak-month` (d) **11/2011**.
- `uk-share` (c) **khoảng 85%** (84.6%).
- `other-share` (b) **khoảng 6%** (5.9%): ngoài UK, thị trường rất phân tán.
- `dec-2011-days` (a) **8 ngày**. (b) 9 là số ngày lịch 1-9/12, quên rằng thứ Bảy 3/12 không bán.
- `no-trading-day` (c) **thứ Bảy**.
- `shortest-full-month` (a) **12/2010** với 20 ngày; 04/2011 có 21 ngày, sát nút. Đây là lý do doanh thu
  mỗi ngày của tháng 12/2010 cao: ít ngày nhưng là mùa cao điểm.
- `dec-per-day` (d) **tăng khoảng 38%**. (a) giảm 58% là con số ngây thơ so tổng tháng dở dang với tổng
  tháng đủ.
- `ceo-chart` (c): giữ dữ liệu, đánh dấu rõ là dở dang, kèm so sánh công bằng. Xoá (a) làm mất tín hiệu
  tốt nhất của quý; vẽ liền (b) tạo cú rơi giả; nhân 31/9 (d) bỏ qua thứ Bảy không bán và mùa vụ trong
  tháng, rồi vẽ ước tính như số thật.
