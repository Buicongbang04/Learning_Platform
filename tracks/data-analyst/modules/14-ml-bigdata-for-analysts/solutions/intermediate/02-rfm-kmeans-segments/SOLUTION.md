# Lời giải: k-means trên RFM và đặt tên segment

## Các hàm

- **`rfm_table`**: lọc dòng hợp lệ có `Customer ID`, `groupby("Customer ID")`: `(snapshot - max(InvoiceDate)).dt.days`,
  `nunique(Invoice)`, `sum(revenue)`. `.dt.days` lấy ngày trọn, nên mua 08:00 ngày 2011-06-01 cho 191 chứ không 192.
- **`prepare_features`**: `np.log1p` rồi `(z - z.mean()) / z.std(ddof=0)`. Log nén đuôi phải (monetary max 280 206 so với
  median 674); chuẩn hoá cho ba cột cùng trọng lượng trong khoảng cách.
- **`fit_kmeans`**: `KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(Z)`.
- **`segment_profile`**: `groupby` theo Series nhãn tên `segment`; median từng cột, tỉ trọng khách và doanh thu, sắp theo
  `monetary_median` giảm dần để thứ tự không phụ thuộc nhãn số.
- **`name_segments`**: hai cờ (`recency_median <= ` median chung, `frequency_median > ` median chung) tra bảng
  `SEGMENT_NAMES`. Quy tắc viết ra được thành một câu, nên ai cũng kiểm lại được vì sao một cụm có tên đó.

## Kết quả trên dữ liệu thật

4 338 khách; median recency 50 ngày, frequency 2 hoá đơn, monetary 674.49 GBP (mean 2 054: lệch phải).

| k | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- |
| Inertia | 6 486 | 4 877 | 3 962 | 3 330 | 2 875 |
| Silhouette | 0.434 | 0.338 | 0.336 | 0.317 | 0.314 |

| Segment | Khách | % khách | Recency median | Hoá đơn median | Doanh thu median (GBP) | % doanh thu |
| --- | --- | --- | --- | --- | --- | --- |
| Champions | 713 | 16.4% | 8 | 10 | 3 729 | 64.7% |
| At risk | 1 187 | 27.4% | 54 | 4 | 1 345 | 24.0% |
| New / promising | 812 | 18.7% | 16 | 2 | 471 | 5.0% |
| Hibernating | 1 626 | 37.5% | 173 | 1 | 298 | 6.3% |

- K-means trên RFM thô (không đổi thang) cho cụm cỡ 4 300 / 5 / 31 / 2: doanh thu chi phối khoảng cách, k-means chỉ tách
  vài khách cực lớn. Vô dụng cho CRM.
- Đổi seed 0 → 7: 99.4% khách giữ cùng tên; 24 khách đổi tên đều nằm ở ranh giới hai cụm kề nhau (nhiều nhất là 11
  khách At risk thành New / promising).

Headline mẫu cho Head of CRM: *"713 khách Champions (16% khách) mang 65% doanh thu năm; 1 187 khách At risk từng mua đều
(median 4 đơn) nhưng gần hai tháng chưa quay lại, giữ 24% doanh thu: đó là nhóm đáng chương trình kéo lại nhất."*

## Đáp án trắc nghiệm

| Câu | Đáp án | Vì sao |
| --- | --- | --- |
| `champions-share` | d | 713 / 4 338 = 16.4% khách, 5.77 triệu / 8.91 triệu GBP = 64.7%. (a) là Hibernating, (b) At risk, (c) New / promising |
| `at-risk-why` | a | Frequency 4 > 2 (thường xuyên), recency 54 > 50 (không gần đây): theo bảng là At risk. (b) là Hibernating; (d) là Champions; (c) sai: doanh thu median thấp nhất là Hibernating |
| `why-not-k2` | b | Silhouette đo độ tách bạch, không đo độ hữu ích. k = 2 chỉ là "khách tốt / còn lại", điều CRM đã biết. k = 3–4 silhouette gần nhau (0.338, 0.336), nên chọn theo số chương trình CRM làm được. (a) đảo nghĩa silhouette; (d) inertia chỉ bằng 0 khi k = số khách |
| `no-scaling` | c | Monetary lên tới 280 206, recency tối đa 373, frequency 209: bình phương khoảng cách gần như chỉ còn monetary, và vài khách cực lớn thành cụm riêng. (a) sai về độ lớn; RFM không có NaN (b) |
| `stability` | b | 99.4% khách giữ tên. Nhãn số có thể đổi giữa hai lần chạy, nên phải so **tên** sau khi đặt theo quy tắc |
| `always-k` | a | K-means luôn chia đúng k cụm, kể cả dữ liệu đều. Nó không tự chọn k (b), nhạy với thang đo (c) và không dùng nhãn (d) |
| `new-customers` | c | Giữ nguyên mô hình: lưu mean/SD của bước chuẩn hoá và tâm cụm (`KMeans.predict`), gán khách mới vào tâm gần nhất; định kỳ (ví dụ mỗi quý) mới fit lại và đối chiếu tên. Fit lại mỗi tháng (a) làm nhãn đổi; (b) bỏ qua dữ liệu; (d) k-means trên 300 khách mới tạo bốn cụm không cùng nghĩa |
| `hibernating-action` | d | Nhóm đông nhưng giá trị thấp: kênh rẻ (email), đo tác động bằng nhóm đối chứng giữ lại không gửi. Gọi điện (a) quá đắt; xoá (b) bỏ mất 6.3% doanh thu và khả năng quay lại; giảm giá sâu cho cả nhóm (c) tốn tiền cho cả những khách sẽ tự quay lại |

## Sai lầm hay gặp

- Chạy k-means trên RFM thô, hoặc chuẩn hoá mà không log: monetary vẫn bị vài khách lớn chi phối.
- Đặt tên theo nhãn số ("cụm 2 là khách VIP") rồi chạy lại notebook và nhãn số đổi.
- Chọn k chỉ theo silhouette hoặc "khuỷu tay" mà không hỏi CRM làm được mấy chương trình.
- Báo "Champions mang 65% doanh thu" mà không nói mẫu số là doanh thu của khách có mã (khách vãng lai không có trong RFM).
- Quên rằng khách mua lần đầu cuối năm có ít thời gian để có frequency cao: New / promising một phần là do exposure ngắn.
