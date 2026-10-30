# Hướng làm: data quality report cho Rossmann store sales

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hai hàm, các phát hiện tham chiếu trên bộ thật, các
quyết định cần cân nhắc và rubric chấm báo cáo.

## Hai hàm

- **`run_checks`**: vòng lặp qua `checks`, mỗi `kind` cho một mặt nạ dòng lỗi: `isna()`;
  `duplicated(columns, keep=False)`; `notna() & ((s < min) | (s > max))`; `notna() & ~isin(values)`;
  `~df.eval(rule).fillna(True).astype(bool)`; kind khác thì `ValueError`. Ghi `failed = int(mask.sum())`,
  `failed_share = failed / len(df)`, `passed = failed == 0`, `severity = check.get("severity", "error")`.
- **`coverage_gaps`**: `full = pd.date_range(min, max, freq="D")` trên cả bảng; với mỗi khoá
  `full.difference(DatetimeIndex(ngày của khoá))`; giữ khoá có ngày thiếu; sắp `missing_days` giảm dần với
  `kind="stable"` sau khi `groupby` đã sắp khoá tăng dần.

## Phát hiện tham chiếu

| Check | Kết quả | Mức độ đề xuất |
| --- | --- | --- |
| Khoá `Store` + `Date` duy nhất, `Sales` không thiếu, trong [0, 41 551] | đạt | |
| `StateHoliday` thuộc `0`, `a`, `b`, `c` (đọc với `dtype=str`) | đạt | |
| Đóng cửa (`Open = 0`) mà có doanh số | 0 | |
| `DayOfWeek` khớp `Date` | đạt | |
| **Độ phủ**: 180 cửa hàng thiếu đúng 184 ngày 01/07-31/12/2014; cửa hàng 988 thiếu 01/01/2013 | 181 cửa hàng | **chặn** cho chỉ số tổng chuỗi |
| Mở cửa mà doanh số 0 | 54 dòng (52 cũng 0 khách; 19 năm 2013, 32 năm 2014, 3 năm 2015) | cần xử lý |
| `CompetitionDistance` thiếu | 3 cửa hàng | ghi chú |
| Có khoảng cách nhưng thiếu `CompetitionOpenSince*` | 351 cửa hàng (354 thiếu tổng) | ghi chú / cảnh báo |
| `CompetitionOpenSinceYear` 1900 (cửa hàng 815), 1961 (cửa hàng 146) | 1 ngoài 1950-2015 | cảnh báo: giá trị mặc định |
| `Promo2 = 0` thì `Promo2Since*` trống và ngược lại | đạt | |
| Cửa hàng ở `train` có trong `store` | đạt | |

Tác động của lỗ hổng độ phủ: nhóm 180 cửa hàng mang khoảng 29-31 triệu doanh số mỗi tháng (5/2014: 30.1 triệu). Tổng
chuỗi theo tháng: 6/2014 190.0 triệu, 7/2014 173.9 triệu (−8.5%), 12/2014 202.1 triệu, 1/2015 198.8 triệu. Dashboard
đọc thẳng tổng chuỗi sẽ báo "doanh số giảm từ tháng 7" và "tháng 1 tăng" sai hoàn toàn. Nhóm thiếu gồm 84 cửa hàng loại
`a`, 81 loại `d`, 14 loại `c`, 1 loại `b`: không phải một loại cửa hàng cụ thể, giống lỗi trích xuất hơn là đóng cửa
thật, nhưng phải hỏi nguồn.

Headline mẫu: **"Dữ liệu Rossmann dùng được cho dashboard, trừ 180 cửa hàng mất trọn 6 tháng cuối 2014"**.

## Các quyết định cần cân nhắc

- **Dòng vắng mặt hay ô trống**: mọi check theo dòng đều đạt mà dữ liệu vẫn sai. Độ phủ là check quan trọng nhất của dữ
  liệu theo thời gian.
- **Mức độ theo tác động, không theo số dòng**: 54 dòng (0.005%) là ghi chú hay cần xử lý tuỳ chỉ số (trung bình ngày
  mở cửa thì có ảnh hưởng); lỗ hổng độ phủ không có dòng lỗi nào nhưng làm sai mọi tổng.
- **Xử lý tạm**: like-for-like (chỉ so cửa hàng có đủ dữ liệu cả hai kỳ) thay vì nội suy 6 tháng doanh số của 180 cửa
  hàng. Không điền `CompetitionOpenSince*` bằng trung vị: tạo ra năm mở cửa giả.
- **Giá trị mặc định của hệ thống** (năm 1900): coi là thiếu, không phải đối thủ mở từ 1900.
- **Check tự động**: những check đã viết nên chạy mỗi lần nạp (dbt tests, pandera, Great Expectations), kèm check số
  cửa hàng có dữ liệu mỗi ngày.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Phạm vi kiểm | 15 | Có đủ nhóm: khoá, thiếu, miền giá trị, quy tắc nghiệp vụ, độ phủ, nhất quán giữa hai bảng; ghi cả check đạt |
| Phát hiện chính | 20 | Tìm ra lỗ hổng 180 cửa hàng × 184 ngày và nói đúng là dòng vắng mặt |
| Tác động | 20 | Gắn mỗi vấn đề với chỉ số trên dashboard và hướng sai; có con số (−8.5% giả tháng 7/2014 hoặc tương đương) |
| Phân loại và mức độ | 15 | Mỗi vấn đề có mức độ hợp lý và nhận định lỗi dữ liệu / quy ước nguồn / sự thật nghiệp vụ, không gọi năm 1900 là sự thật |
| Khuyến nghị | 15 | Việc cụ thể, người làm, thời điểm; xử lý tạm cho dashboard (like-for-like); check tự động mỗi lần nạp |
| Viết cho người đọc | 10 | Headline trả lời "dùng được chưa"; người đọc không cần biết pandas; bảng kết quả gọn |
| Giới hạn | 5 | Ít nhất hai giới hạn hoặc câu hỏi mở cụ thể |

Từ 70 điểm trở lên là báo cáo gửi được cho team BI.

## Sai lầm hay gặp

- Chỉ chạy `df.isna().sum()` và `df.describe()`, kết luận "dữ liệu sạch": bỏ sót lỗ hổng lớn nhất.
- Đọc `train.csv` không có `dtype={"StateHoliday": str}`: pandas có thể trộn `0` (số) và `"0"` (chuỗi), check miền giá
  trị báo lỗi giả.
- Nội suy doanh số 6 tháng cho 180 cửa hàng để "lấp" lỗ hổng rồi đưa vào dashboard như số thật.
- Báo cáo liệt kê 30 check theo thứ tự code, không nói cái nào chặn, cái nào bỏ qua được.
