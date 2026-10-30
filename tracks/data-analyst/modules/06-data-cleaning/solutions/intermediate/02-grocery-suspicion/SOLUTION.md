# Lời giải: nghi ngờ dữ liệu Grocery Sales

## Cách làm

- **`sales_profile`**: một `SELECT` với `count(*)`, `count(DISTINCT TransactionNumber)`, subquery `max(n)` trên
  `GROUP BY TransactionNumber`, hai `avg(CASE ...)`, `min`/`max(Quantity)`; `fetchone()` rồi ép kiểu. Toàn bộ chạy
  trong DuckDB, chỉ một dòng về Python; trên laptop 4 GB với `memory_limit = '1GB'` mất vài giây.
- **`count_by`**: `SELECT {expr} AS k, count(*) AS n FROM {table} WHERE {expr} IS NOT NULL GROUP BY 1 ORDER BY 1`,
  `set_index("k")["n"]`.
- **`uniformity_test`**: `scipy.stats.chisquare(counts)` (không truyền `f_exp` là kỳ vọng đều); `max / min`.
- **`dispersion_index`**: `counts.var() / counts.mean()`.
- **`red_flags`**: dict cờ → điều kiện, rồi lọc theo `FLAG_ORDER`.

## Bằng chứng trên bộ thật

| Chiều | Grocery Sales | Siêu thị thật (dunnhumby) |
| --- | --- | --- |
| Dòng mỗi giao dịch | 1 (6 758 125 giao dịch, 6 758 125 dòng) | trung vị 5, trung bình 9.4, tối đa 168 dòng/giỏ |
| `TotalPrice` | 100% bằng 0 | 0.7% dòng `SALES_VALUE = 0` |
| `Quantity` | 1 tới 25, mỗi giá trị khoảng 4% dòng; chi2 23.19, p 0.509 | 79% dòng mua 1 đơn vị, 96% mua 1-3 |
| Giờ trong ngày | p 0.860, giờ đông nhất / vắng nhất 1.006 (3h sáng như 18h) | 17h đông gấp khoảng 100 lần 4h |
| Số dòng mỗi ngày | phương sai / trung bình 0.92 (Poisson), trung bình mỗi ngày theo thứ 51 828-51 921 | 388 (cả 711 ngày), 154 (ngày 100-600) |
| Nhân viên (23) | p 0.429, max/min 1.008 | không có cột này |
| Sản phẩm (452) | p 0.993, max/min 1.046; giá đều 0.04-99.88 (KS p 0.42) | không đều |
| Khách (98 759) | phương sai / trung bình 0.995 (Poisson) | 961 (số dòng mỗi hộ) |
| Thiếu `SalesDate` | 67 526 dòng = 1.0%, đều | không thiếu |
| Bảng chiều | Mỹ mã `AR`, Canada `FO`; 96 thành phố đều thuộc Mỹ, mỗi thành phố 964-1 104 khách; rượu vang trong "Snails", "Grain"; thịt bò thăn 3.33 | không áp dụng |

Bẫy thứ trong tuần: tổng theo thứ cho chi2 p gần 0 vì 01/01-09/05/2018 có 19 thứ Hai, Ba, Tư và 18 các thứ khác.
Trung bình **mỗi ngày** theo thứ chỉ chênh 51 828 tới 51 921 dòng (0.2%).

## Trả lời cho 5 yêu cầu

| Báo cáo | Vì sao không giao insight |
| --- | --- |
| Doanh thu theo tháng, danh mục | `TotalPrice` toàn 0. Tính lại `Price × Quantity × (1 − Discount)` cho ra một con số, nhưng giá sinh đều 0-100 không liên quan tới sản phẩm, danh mục ghép ngẫu nhiên (rượu vang trong "Snails") |
| Giỏ hàng, mua cùng | Mỗi giao dịch 1 dòng: không có giỏ |
| Giờ cao điểm | Mọi giờ bằng nhau trong sai số ngẫu nhiên; "giờ cao nhất" là nhiễu, xếp ca theo nó là sai |
| Khách VIP theo thành phố | Số dòng mỗi khách là Poisson; thành phố gắn ngẫu nhiên; VIP là người may mắn trong phép rút thăm |
| Xếp hạng nhân viên | Chênh lệch giữa người nhất và người bét 0.8%, đúng bằng nhiễu ngẫu nhiên; thưởng theo đó là thưởng theo xổ số |

Kết luận mẫu (dòng đầu email): **"Bộ Grocery Sales là dữ liệu sinh giả: em không báo cáo insight nào từ bộ này. Để có
5 báo cáo, cần bản xuất POS thật có mã giỏ, giá bán và giờ giao dịch."** Bộ này vẫn dùng được để tập SQL nhiều bảng và
thiết kế schema (module 09), miễn là không ai đọc con số như sự thật.

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `basket-size` | b. 1 dòng | `max_lines_per_transaction = 1`; 168 là giỏ lớn nhất của dunnhumby |
| `quantity-p` | c. khoảng 0.51 | chi2 23.19 với 24 bậc tự do |
| `daily-dispersion` | d. khoảng 0.92 | Gần 1 như đếm Poisson; dunnhumby 388 |
| `missing-date` | a | 67 526 / 6 758 125 = 0.999%; một tỉ lệ tròn, rải đều, kiểu "đục lỗ" khi sinh dữ liệu |
| `weekday-trap` | c | Số ngày mỗi thứ khác nhau; luôn chuẩn hoá theo số ngày trước khi so |
| `p-meaning` | a | p-value không phải xác suất giả thuyết đúng; với n lớn, dữ liệu thật hầu như luôn bị bác bỏ "đều" |
| `reports-possible` | d. 0 | Xem bảng trên; "kèm chú thích" vẫn là đưa số giả vào phòng họp |
| `reply` | b | Kết luận trước, rồi việc cần làm; không giao dashboard rồi giấu cảnh báo ở phụ lục |

## Sai lầm hay gặp

- `pd.read_csv` cả 517 MB trên laptop 4 GB: tràn RAM. Dùng DuckDB hoặc `usecols` + `dtype` + đọc theo khúc.
- Tự "sửa" `TotalPrice` bằng `Price × Quantity` rồi báo cáo doanh thu: sửa được cột không làm dữ liệu thành thật.
- Dừng ở một kiểm định: một chiều phẳng có thể là trùng hợp; sáu chiều độc lập cùng phẳng cộng lỗi logic ở bảng chiều
  mới là bằng chứng đủ nặng.
- Viết "không có giờ cao điểm, nhân viên làm việc đồng đều" như một insight: đó chính là báo cáo insight từ dữ liệu giả.
