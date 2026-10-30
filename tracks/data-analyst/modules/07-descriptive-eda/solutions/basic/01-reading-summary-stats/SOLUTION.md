# Lời giải: đọc bảng thống kê mô tả

## Cách đọc một bảng `describe()`

1. **count trước**: nó cho biết tổng thể. `TotalCharges` có 7 032 so với 7 043; `Sales` mọi dòng có 1 017 209
   so với 844 338 ngày mở cửa. Hai cột khác count là hai câu hỏi khác nhau.
2. **mean so với 50%**: hướng lệch và mức lệch.
3. **25%–75%**: nửa giữa, thường là câu trả lời tốt cho "bình thường thì thế nào" trên dữ liệu lệch.
4. **min/max**: miền giá trị, lỗi nhập, mức trần (`tenure` tối đa 72 tháng là mức trần của dữ liệu).
5. **skew/kurt**: có nên tin một con số tóm tắt không, và cần vẽ gì.

## Đáp án từng câu

| Câu | Đáp án | Vì sao |
| --- | --- | --- |
| `tenure-shape` | c | Excess kurtosis −1.39 là đuôi rất nhẹ, dấu hiệu phân phối phẳng hoặc nhiều đỉnh. Thật vậy, `tenure` hình chữ U: mode ở tháng 1 (613 khách) và một cụm ở tháng 72 (362 khách). Skew 0.24 gần 0 không có nghĩa là chuẩn (a); không có đuôi phải dài (b) hay outlier (d): max 72 chỉ cách p75 17 tháng |
| `monthly-mean-below-median` | a | Mean < median nghĩa là có phần bị kéo về bên trái: 1 526 khách không dùng internet trả TB 21.08 USD. (b) mô tả trường hợp ngược lại; (c) sai vì `MonthlyCharges` có count 7 043, không thiếu; (d) mean và median chênh 5.6 USD, và kurt −1.26 không phải chuẩn |
| `totalcharges-count` | b | pandas, SQL `AVG`, Excel `AVERAGE` đều bỏ qua ô thiếu. 11 ô trống là khách `tenure = 0`, chưa có hoá đơn; mean là của 7 032 khách còn lại. Điền 0 (a) hay mean (c) là quyết định bạn phải tự đưa ra và ghi lại, pandas không làm thay |
| `which-sales-mean` | d | "Một ngày bán hàng bình thường": tập dòng là ngày mở cửa, và "bình thường" trên dữ liệu skew 1.59 là median. Mean mọi dòng (a) và median mọi dòng (b) trộn 17% ngày đóng cửa có doanh số 0; mean ngày mở cửa (c) đúng tập dòng nhưng bị các ngày lớn kéo lên 9% so với median. Nếu câu hỏi là "dự báo doanh số cả tháng" thì cần mean (hoặc tổng) mọi dòng |
| `skew-drops-with-zeros` | b | 172 871 dòng bằng 0 (17.0%) tạo một khối ở tận cùng bên trái, cân lại phần đuôi phải; mean cũng tụt xuống gần median (5 774 so với 5 744). Mean ≈ median và skew thấp ở đây **không** có nghĩa là "doanh số ngày phân phối đẹp": nó là hỗn hợp hai tổng thể. (c) sai: ngày đóng cửa có doanh số 0 |
| `middle-half` | d | Nửa giữa là p25–p75 **của ngày mở cửa**. (b) là p25–p75 của mọi dòng, gồm ngày đóng cửa; (a) mean ± 1 SD chỉ chứa khoảng 68% khi phân phối gần chuẩn, ở đây lệch phải; (c) là toàn miền |
| `customers-kurt` | a | Excess kurtosis 13.32 là đuôi nặng: có những ngày số khách rất cao (max 7 388, gần gấp 10 lần median 676). Kurtosis không đo độ nhọn (b); hai đỉnh thường cho kurtosis **âm** (c); kurtosis không có giới hạn trên 3 (d) |
| `cv-two-stores` | c | So biến động giữa hai quy mô khác nhau dùng CV = SD / mean: 1 598 / 2 901 = 0.55 so với 4 675 / 21 757 = 0.21. SD tuyệt đối (a) chủ yếu phản ánh quy mô. Cửa hàng 198 là cửa hàng có CV cao nhất trong 1 115 cửa hàng |
| `excel-std` | d | pandas `std()` mặc định chia n − 1 (mẫu); `STDEV.P` chia n (tổng thể). Với n = 12, bản mẫu lớn hơn hệ số căn bậc hai của 12/11, khoảng 4.4%. (b) nhầm `STDEV.P` với `STDEV.S`. Luôn ghi rõ bản nào; nếu 12 tháng là toàn bộ năm bạn mô tả, `STDEV.P` là hợp lý |
| `warehouse-median` | b | Tính ở nơi dữ liệu nằm và lặp lại được: Postgres và các warehouse tương thích dùng `percentile_cont(0.5) WITHIN GROUP (ORDER BY x)` (không có `median()`), đặt trong view để báo cáo tuần dùng chung. Xuất 2 tỉ dòng (a) không khả thi; median không gần mean trên giá trị đơn (c); mẫu thủ công trong Excel (d) không tái lập và có sai số mẫu |

## Con số tham chiếu

| Đại lượng | Giá trị |
| --- | --- |
| Khách `tenure = 1` / `tenure = 72` | 613 / 362 |
| Cước TB nhóm không internet / DSL / cáp quang | 21.08 / 58.10 / 91.50 USD |
| Dòng Rossmann đóng cửa (`Open = 0`) / mở cửa nhưng doanh số 0 | 172 817 / 54 |
| Tỉ lệ dòng có `Sales = 0` | 17.0% |
| Cửa hàng 817: mean, SD, CV | 21 757, 4 675, 0.215 |
| Cửa hàng 198: mean, SD, CV | 2 901, 1 598, 0.551 |
