# Lời giải: MapReduce bằng tay

## Các hàm

- **`valid_lines`**: mặt nạ `~Invoice.astype(str).str.startswith("C") & (Quantity > 0) & (Price > 0)`, `.copy()` rồi thêm
  `revenue`. Không lọc `Customer ID`: doanh thu theo nước tính cả khách vãng lai (khác bài phân khúc khách).
- **`split_chunks`**: `np.array_split(np.arange(len(df)), n)` cho vị trí dòng, `df.iloc[idx]` cho khối. Chia theo vị trí,
  không theo nội dung: đó là cách HDFS cắt tệp thành block 128 MB mà không biết block chứa nước nào.
- **`map_revenue` / `map_words`**: chỉ nhìn một khối, trả dict. `map_words` dùng `Counter` và
  `re.findall(r"[a-z]+", text.lower())`; `dropna()` bỏ tên trống.
- **`reduce_counts`**: `total[k] = total.get(k, 0) + v`. Hàm này dùng được cho cả hai mapper vì phép gộp là phép cộng.
- **`run_mapreduce`**: `split_chunks` → `[mapper(c) ...]` khi 1 worker, `ctx.Pool(n).map(mapper, chunks)` khi nhiều worker
  → `reduce_counts`. Dùng context `"fork"` khi có để tiến trình con thừa hưởng hàm định nghĩa trong notebook.

## Con số tham chiếu (sheet `Year 2010-2011`)

| Đại lượng | Giá trị |
| --- | --- |
| Dòng hợp lệ | 530 105 |
| Doanh thu gộp, 38 nước | 10 666 702.54 GBP |
| Top 5 nước | United Kingdom 9 025 222 (84.6%), Netherlands 285 446 (2.7%), EIRE 283 454 (2.7%), Germany 228 867 (2.1%), France 209 733 (2.0%) |
| Lệch giữa map-reduce 4 khối và `groupby` | cỡ 2e-9 GBP (thứ tự cộng số thực) |
| Từ khác nhau trong tên sản phẩm | 2 062 |
| Top từ | set 62 760, of 53 383, bag 51 186, red 42 602, heart 38 783, retrospot 34 400, vintage 33 247, design 29 544, pink 29 454, christmas 24 840 |
| Thời gian trên máy kiểm (thay đổi theo máy) | groupby 0.17 s; 1 worker 0.13 s; 2 worker 0.61 s; 4 worker 0.55 s |

Trả lời Head of Analytics:

- **Spark làm gì khác?** Cùng một phép tính, chia thành khối, mỗi máy map khối của nó, gom theo khoá, reduce. Kết quả
  khớp `groupby` tới phần tỉ GBP; khác biệt duy nhất là thứ tự cộng số thực.
- **Có nhanh hơn không?** Với 530 nghìn dòng (dưới 100 MB trong RAM), không: tạo tiến trình và gửi các khối DataFrame
  sang tiến trình con tốn hơn phần tính toán. Spark còn thêm chi phí khởi động cụm và lập lịch. Lợi ích chỉ đến khi
  dữ liệu không vừa một máy hoặc phần tính toán nặng hơn chi phí truyền dữ liệu nhiều lần.
- **Đề xuất**: giữ báo cáo trên pandas/DuckDB; xem lại khi dữ liệu đã nằm trong lakehouse hoặc tăng tới mức một máy
  không xử lý kịp lịch chạy.

## Đáp án trắc nghiệm

| Câu | Đáp án | Vì sao |
| --- | --- | --- |
| `uk-share` | c | 9 025 222 / 10 666 703 = 84.6%. Mọi nước ngoài Anh cộng lại chỉ khoảng 15% |
| `top3-countries` | b | Netherlands 285 446 GBP, EIRE 283 454 GBP: chênh chưa tới 1%, nên (c) là bẫy đọc vội. Germany đứng thứ 4 |
| `stopword` | b | `of` là từ chức năng (stop word), không nói gì về sản phẩm; "red heart", "retrospot" (một dòng sản phẩm) mới có ích. Số đếm đúng (a) không có nghĩa là hữu ích; Spark (c) cho cùng kết quả; (d) vô nghĩa vì cách chia khối là tuỳ ý |
| `float-diff` | c | Phép cộng số thực không kết hợp tuyệt đối: (a + b) + c có thể khác a + (b + c) ở chữ số cuối. Mỗi dòng nằm đúng một khối (a sai); pickle không làm tròn (b sai); `pandas_revenue` cũng không lọc `Customer ID` (d sai) |
| `parallel-slower` | d | Mỗi worker là một tiến trình mới; khối DataFrame phải được `pickle` và gửi qua. Với dữ liệu nhỏ, chi phí này lớn hơn thời gian tính. GIL (b) chỉ áp dụng cho luồng (thread), không cho tiến trình; (a), (c) không đúng với máy thông thường |
| `mean-mapreduce` | d | Trung bình không cộng dồn được; (tổng, đếm) thì được. Trung bình của trung bình (a) sai khi các khối có số dòng khác nhau (module 07). Median của median (b) không phải median; gửi mọi dòng (c) mất ý nghĩa của map |
| `median-distributed` | a | Median cần biết thứ tự của mọi giá trị trong nhóm; không có kết quả từng phần nhỏ nào gộp lại ra median chính xác. Spark có `percentile` chính xác nhưng tốn bộ nhớ và shuffle; bản xấp xỉ dùng sketch gộp được |
| `when-spark` | a, c | Spark hợp khi dữ liệu đã ở hệ sinh thái Spark hoặc vượt một máy. Với 1 triệu dòng (b), Spark chậm hơn pandas/DuckDB; (d) không phải lý do kỹ thuật hay kinh doanh |

## Sai lầm hay gặp

- Chia khối theo `Country` (mỗi nước một khối) rồi bảo map đã "song song": đúng kết quả nhưng sai mô hình, và một
  khối United Kingdom chiếm 90% dữ liệu (skew), đúng vấn đề Spark gặp khi một khoá quá lớn.
- Map trả trung bình rồi reduce lấy trung bình.
- Quên `.copy()` trong `valid_lines` rồi thêm cột trên lát cắt: cảnh báo `SettingWithCopyWarning`, có khi sửa nhầm dữ liệu
  gốc.
- Kết luận "song song luôn nhanh hơn" mà không đo; hoặc đo một lần duy nhất ngay sau khi khởi động kernel.
