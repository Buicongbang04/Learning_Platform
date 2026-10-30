# Lời giải: khi mean lừa

## Cách làm

1. **`trimmed_mean`**: kiểm `0 <= prop < 0.5`, `x = np.sort(...dropna())`, `k = int(prop * len(x))` (floor như
   `scipy.stats.trim_mean`), mean của `x[k:len(x) - k]`. Dùng `len(x) - k` thay cho `-k` để `k = 0` không ra mảng
   rỗng.
2. **`winsorized_mean`**: kiểm `0 <= lower < upper <= 1`, `x.clip(x.quantile(lower), x.quantile(upper)).mean()`.
   Số quan sát giữ nguyên; chỉ giá trị ở đuôi bị kéo về ngưỡng.
3. **`share_within`**: `x.between(center - width, center + width).mean()` trên phần không NaN (mặc định tính cả
   hai đầu).
4. **`mean_without_top`**: mảng đã sắp, `x[:len(x) - k].mean()`, `ValueError` khi `k < 0` hoặc `k >= n`.

## Vì sao như vậy

**Nhiều đỉnh.** Cước tháng có mean 64.76, median 70.35, mode 20.05 USD, nhưng chỉ 7.6% khách có cước trong mean
± 5 USD (11.6% quanh median). Ba nhóm khách có mức cước khác hẳn: không internet 1 526 khách, TB 21.08; DSL
2 421 khách, TB 58.10; cáp quang 3 096 khách, TB 91.50. Mean rơi vào khoảng giữa DSL và cáp quang, median rơi vào
sườn của nhóm cáp quang. Không con số nào là "khách điển hình", nên trả lời Marketing **theo nhóm** (và SD trong
nhóm nhỏ: 2.16, 16.26, 12.66 so với 30.09 chung). Trimmed mean (64.97) không giúp gì: nó chống đuôi, không chống
nhiều đỉnh.

**Số 0 và tập dòng.** Mọi dòng của `train.csv`: mean 5 773.8, median 5 744.0, skew 0.64, 17.0% là 0. Ngày mở cửa
có bán: mean 6 956.0, median 6 369.0, skew 1.59. Mean gần median trên mọi dòng là ảo giác do trộn hai tổng thể
(ngày đóng cửa và ngày bán), không phải dấu hiệu phân phối đối xứng. Câu hỏi "một ngày bán hàng bình thường" dùng
ngày mở cửa (median 6 369); câu hỏi "doanh số cả tháng" dùng mean **mọi dòng** (hoặc tổng), vì tháng tới cũng sẽ
có ngày đóng cửa.

**Đuôi dài và cực trị.**

| | `CompetitionDistance` (m) | Doanh số TB mỗi cửa hàng (EUR) |
| --- | --- | --- |
| n | 1 112 | 1 115 |
| mean / median | 5 404.9 / 2 325.0 | 6 934.6 / 6 589.9 |
| trimmed 10% / winsorized 5–95% | 3 775.0 / 4 932.9 | 6 676.4 / 6 820.3 |
| mean bỏ top 10 | 5 020.3 (−7.1%) | 6 826.5 (−1.6%) |
| skew / tỉ lệ lớn hơn mean | 2.93 / 29.3% | 1.75 / 44.0% |

Khoảng cách tới đối thủ lệch rất mạnh: 10 cửa hàng xa nhất (0.9%) kéo mean 7%, và 71% cửa hàng gần đối thủ hơn
mean. Trả lời team mở rộng bằng median 2 325 m kèm p25–p75 (718–6 883 m). Doanh số trung bình mỗi cửa hàng lệch
vừa phải; mean vẫn dùng được cho tổng, median cho "cửa hàng điển hình".

**Outlier thật không bị xoá.** Cửa hàng 817 là cửa hàng thật bán nhiều nhất, không phải lỗi. Xoá nó làm tổng
doanh số chuỗi sai. Cách đúng: giữ trong mọi tổng; với câu hỏi "điển hình" dùng median hoặc trimmed mean; nếu nghi
lỗi dữ liệu thì kiểm với chủ dữ liệu trước khi sửa, và ghi lại.

## Đáp án trắc nghiệm

- `near-mean` (a) 7.6%. (b) 11.6% là quanh median; (d) 68% là quy tắc của phân phối chuẩn trong ± 1 SD.
- `report-charges` (c): báo theo nhóm. Mean (a), median (b), mode (d) đều là một con số cho dữ liệu ba đỉnh.
- `trimmed-distance` (d) 3 775 m. (a) là winsorized mean, (b) là mean bỏ top 10, (c) là p75.
- `above-mean` (b) 29.3%.
- `top10-store` (c) 6 827 EUR. (a) 6 921 là mean khi chỉ bỏ cửa hàng lớn nhất; (d) là mean mọi dòng của doanh số
  ngày, một con số khác hẳn.
- `forecast-total` (b): dự báo tổng cần mean (cộng được), và trên đúng tập dòng của tháng tới (có cả ngày đóng
  cửa). Median (a), trimmed mean (c), mode (d) nhân lên không ra tổng.
- `drop-outliers` (b): giữ trong tổng, dùng thống kê robust cho câu hỏi điển hình.
