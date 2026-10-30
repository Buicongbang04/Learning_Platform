# Lời giải: lưới lịch, resample tuần và kỳ chưa đủ

## Cách làm

- **`clean_sales`**: ép `Invoice` sang `str` trên một bản sao (`assign`), lọc theo quy tắc chung, thêm `revenue`.
- **`daily_revenue`**: `set_index("InvoiceDate")["revenue"].resample("D").sum()`. `resample` tự tạo lưới mọi ngày từ
  ngày đầu tới ngày cuối và điền **0** cho ngày không có dòng (với `sum`; với `mean` thì là `NaN`). Đặt tên index
  `date`, tên Series `revenue`.
- **`daily_average`**: tổng chia `len(daily)` và chia `(daily > 0).sum()`.
- **`weekly_report`**:

```python
weeks = daily.resample("W-SUN")
out = pd.DataFrame({
    "revenue": weeks.sum(),
    "trading_days": (daily > 0).resample("W-SUN").sum().astype(int),
    "calendar_days": weeks.size().astype(int),
})
out["complete"] = out["calendar_days"] == 7
out["rolling_4w"] = out["revenue"].where(out["complete"]).rolling(4).mean()
```

  `size()` đếm số ngày lịch **có trong `daily`** của mỗi tuần, nên tuần đầu (01–05/12/2010) và tuần cuối (05–09/12/2011)
  ra 5. `where(complete)` biến tuần chưa đủ thành `NaN` và `rolling(4)` mặc định trả `NaN` cho cửa sổ có `NaN`, nên
  đường xu hướng không bị tuần cuối kéo lên.

## Con số chính

| Đại lượng | Giá trị |
| --- | --- |
| Ngày lịch / ngày có đơn | 374 / 305 |
| Ngày không có đơn | 69: 53 thứ Bảy, 9 ngày nghỉ Giáng sinh (24/12/2010 – 03/01/2011), 7 ngày lễ 2011 (22, 24, 25, 29/4; 2/5; 30/5; 29/8) |
| Trung bình mỗi ngày lịch / ngày có bán | 28 520.60 / 34 972.80 GBP (chênh 22.6%) |
| Trung bình theo thứ (mọi ngày của thứ đó) | T3 41 106, T5 40 799, T4 34 281, T6 34 081, T2 33 577, CN 15 355, T7 0 GBP |
| Số tuần / tuần đủ | 54 / 52 |
| Tuần cao nhất | kết thúc 11/12/2011, 5 ngày, 504 328 GBP, trong đó hoá đơn 581483 (80 995 cái PAPER CRAFT, LITTLE BIRDIE, 168 470 GBP) bị huỷ bằng C581484 12 phút sau |
| Tuần đủ cao nhất | kết thúc 20/11/2011, 388 622 GBP |
| Tuần đủ thấp nhất | kết thúc 02/01/2011, 0 GBP (nghỉ lễ) |
| Trung bình 4 tuần đủ, tuần kết thúc 04/12/2011 | 349 863 GBP |

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `closed-weekday` | c | Cả 53 thứ Bảy đều không có đơn: cửa hàng không nhận đơn thứ Bảy |
| `two-denominators` | a | 28 521 và 34 973 GBP |
| `non-saturday-zero` | b | 9 ngày Giáng sinh – năm mới + 7 ngày lễ năm 2011 (Phục sinh, đám cưới hoàng gia 29/4, các bank holiday) |
| `weakest-open-day` | d | Chủ nhật 15 355 GBP, chưa bằng một nửa các ngày trong tuần: Chủ nhật có mở nhưng ít đơn |
| `best-week` | d | Tuần cuối chưa đủ 7 ngày vẫn cao nhất vì một hoá đơn 168 470 GBP bị huỷ ngay; bỏ nó ra còn khoảng 335 858 GBP. Không gọi là kỷ lục |
| `zero-week` | a | Tuần nghỉ lễ là thật, không phải lỗi; giữ trong dữ liệu, chú thích trên chart, và so cùng kỳ năm trước thay vì so với tuần liền trước |
| `resample-zero` | b | 0 là quy ước của `sum` trên nhóm rỗng; nghỉ, lễ hay mất dữ liệu là kiến thức nghiệp vụ, phải kiểm |
| `rolling-on-transactions` | c | `rolling(7)` trên bảng dòng là 7 dòng hàng liên tiếp (vài phút của một hoá đơn), không phải 7 ngày. Phải đưa lên chuỗi ngày trước |

## Ba câu cho trưởng bộ phận vận hành (mẫu)

1. Trong 12 tháng tới 09/12/2011, cửa hàng bán trung bình **35 nghìn GBP mỗi ngày có nhận đơn** (305 ngày); nếu chia
   cho mọi ngày lịch thì 28.5 nghìn. Kế hoạch nhân sự kho nên dùng con số theo ngày làm việc, và tính riêng thứ Ba,
   thứ Năm (khoảng 41 nghìn) với Chủ nhật (15 nghìn).
2. Không có đơn vào mọi thứ Bảy, tuần Giáng sinh – năm mới (24/12 – 03/01) và 7 ngày lễ trong năm; cần xác nhận với
   bạn đây là lịch nghỉ thật chứ không phải hệ thống ngừng ghi nhận.
3. Tuần cao nhất trong bảng (kết thúc 11/12/2011, 504 nghìn GBP) là tuần chưa đủ và chứa một hoá đơn 168 nghìn GBP bị
   huỷ ngay sau đó; tuần đủ cao nhất là tuần kết thúc 20/11/2011 (389 nghìn GBP), và đường xu hướng 4 tuần đứng ở
   khoảng 350 nghìn GBP/tuần đầu tháng 12.

## Lỗi hay gặp

- Tính `groupby(InvoiceDate.dt.date).sum().mean()`: chỉ có ngày có đơn, không ai biết mẫu số là 305.
- `rolling(7)` trên bảng giao dịch hoặc trên chuỗi ngày chưa đủ lưới.
- Vẽ tuần mà không đánh dấu tuần đầu/cuối chưa đủ: một "kỷ lục" giả và một "sụt giảm" giả ở hai đầu.
- Dùng doanh thu gộp mà không nói rõ: hoá đơn 581483 được tính vì nó hợp lệ tại thời điểm xuất, dù bị huỷ 12 phút sau
  (xem cách xử lý đơn huỷ sau ở module 08 Advanced 01).
