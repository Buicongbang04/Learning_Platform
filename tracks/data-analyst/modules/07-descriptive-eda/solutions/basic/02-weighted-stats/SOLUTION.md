# Lời giải: thống kê có trọng số

## Cách làm

1. **Hàm phụ `_pairs(x, w)`** gom phần kiểm tra: đổi sang `np.asarray(dtype=float)` (bỏ index của Series, tránh
   căn hàng sai), kiểm cùng độ dài, bỏ cặp có NaN, kiểm `w >= 0` và tổng `> 0`. Ba hàm chính dùng chung, nên quy
   tắc làm sạch chỉ nằm một chỗ.
2. **`weighted_mean`**: `(w * x).sum() / w.sum()`.
3. **`weighted_std`**: tính mean có trọng số, tổng bình phương độ lệch nhân trọng số, chia cho `w.sum() - ddof`.
   Với trọng số tần suất, `w.sum()` chính là n của dữ liệu đã nhân bản, nên `ddof=1` khớp pandas.
4. **`weighted_quantile`**: bỏ thêm trọng số 0 (nếu không, `q = 0` có thể trả về một giá trị không có ai), sắp
   theo `x`, cộng dồn trọng số, `np.searchsorted(cum, q * cum[-1], side="left")`, chặn chỉ số ở `len(x) - 1`
   cho an toàn khi làm tròn.

## Vì sao như vậy

- **Bảng tần suất là dữ liệu đã nén**, không phải dữ liệu mới: mỗi dòng là `w` khách giống nhau. Mọi thống kê
  phải tính như khi giải nén. Lấy mean cột giá trị (36.00) là cho mỗi **giá trị** một phiếu thay vì mỗi
  **khách** một phiếu; mean đúng là 32.37.
- **Trung bình các tỉ lệ** là cùng lỗi ở dạng khác: ba tỉ lệ churn theo hợp đồng có mean 18.9%, trong khi tỉ lệ
  chung là 26.5%, vì nhóm month-to-month (42.7%) có 3 875 khách, nhiều hơn hai nhóm kia cộng lại. Mean có trọng
  số theo số khách của các tỉ lệ nhóm luôn bằng tổng số khách churn / tổng số khách.
- **Tỉ số mỗi dòng**: mean các tỉ số `Sales / Customers` có trọng số theo `Customers` là
  $$\sum_i C_i \frac{S_i}{C_i} / \sum_i C_i = \sum_i S_i / \sum_i C_i$$, tức tổng/tổng (9.12 EUR). Mean không
  trọng số (9.49) cho ngày 200 khách và ngày 2 000 khách cùng một phiếu; ngày đông khách có giá trị mỗi khách
  thấp hơn, nên con số không trọng số cao hơn. Câu hỏi của CFO là về **mỗi khách**, nên dùng 9.12.
- **Median có trọng số** theo số khách (8.86) là "khách ở giữa": một nửa số khách mua ở cửa hàng-ngày có giá trị
  mỗi khách dưới 8.86 EUR. Median không trọng số (9.25) là "cửa hàng-ngày ở giữa".
- **Bảng chia nhóm**: dùng điểm giữa nhóm làm `x` là xấp xỉ (giả định khách phân bố đều trong nhóm). Trên 6 nhóm
  12 tháng, mean ra 32.48 so với 32.37 thật; nhóm càng rộng hoặc phân phối trong nhóm càng lệch thì sai số càng
  lớn. Median và quantile từ bảng chia nhóm chỉ xác định được tới nhóm chứa nó.

## Con số tham chiếu (bộ thật)

| Đại lượng | Giá trị |
| --- | --- |
| Khách / số giá trị `tenure` khác nhau | 7 043 / 73 |
| Mean, SD mẫu, SD tổng thể `tenure` | 32.371, 24.559, 24.558 |
| p25, median, p75 `tenure` | 9, 29, 55 tháng |
| Mean cột giá trị của bảng tần suất (sai) | 36.00 |
| Churn theo hợp đồng: month-to-month, 1 năm, 2 năm | 42.7%, 11.3%, 2.8% (3 875, 1 473, 1 695 khách) |
| Mean ba tỉ lệ / tỉ lệ chung | 18.9% / 26.5% |
| Rossmann cửa hàng-ngày mở cửa có bán | 844 338 |
| EUR/khách: mean tỉ số, tổng/tổng, median, median theo khách | 9.494, 9.119, 9.25, 8.861 |

## Đáp án trắc nghiệm

- `freq-table-mean` (b): mean 73 giá trị 0..72 là 36.00; mean đúng theo khách là 32.37. (a) 29 là median.
- `churn-overall` (d): 26.5%, nhóm churn cao nhất cũng đông nhất.
- `sales-per-customer` (a): tổng/tổng. (b), (c) là thống kê của cửa hàng-ngày; (d) là median theo khách, không
  phải mean.
- `why-ratio-gap` (b): ngày đông khách có EUR/khách thấp hơn nhưng trong mean tỉ số chỉ có một phiếu như ngày
  vắng. (a) sai: cả hai cách đều chỉ dùng ngày mở cửa có bán.
- `ddof-weights` (c): n là tổng trọng số (số khách), nên chia cho số khách − 1.
- `bucket-midpoint` (c): xấp xỉ khá sát (32.48 so với 32.37), sai số đến từ giả định khách đều trong nhóm.
- `excel-weighted` (b): `SUMPRODUCT` nhân từng cặp rồi cộng, chia `SUM` trọng số.
