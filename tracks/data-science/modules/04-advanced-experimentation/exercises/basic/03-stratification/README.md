---
title: Stratified sampling và post-stratification
level: basic
services: []
files:
  - path: starter/strata.py
    note: 3 hàm TODO
  - path: tests/test_strata.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/04-advanced-experimentation/exercises/basic/03-stratification -q
---

## Mục tiêu

Dùng thông tin "đơn vị này thuộc nhóm nào" để thí nghiệm nhạy hơn, theo hai cách: chia tầng ngay lúc
random (stratified sampling, kiểu Netflix) hoặc chia tầng lúc phân tích (post-stratification). Biết
khi nào mỗi cách đáng công.

## Đề bài

Trong `starter/strata.py`:

1. `strata_from_quantiles(x, q)`: nhãn tầng `0..q-1` theo quantile của `x` (doanh số trước thí
   nghiệm, số đơn năm ngoái…). Tầng `q-1` chứa giá trị lớn nhất.
2. `stratified_assign(strata, seed=0)`: mảng bool, trong **mỗi** tầng số treatment và control lệch
   nhau tối đa 1. Thứ tự trong tầng phải ngẫu nhiên, và ở tầng có số lẻ đơn vị, nhánh nhận đơn vị
   thừa cũng phải ngẫu nhiên (nếu luôn cho control thì 50 tầng lẻ thành lệch 50 đơn vị).
3. `post_stratified_effect(y, treat, strata, alpha=0.05) -> dict`: `diff`, `se`, `ci_low`,
   `ci_high` theo công thức

$$
\hat\tau_{\text{post}} = \sum_k w_k\left(\bar y_{T,k} - \bar y_{C,k}\right),
\qquad
\widehat{\mathrm{var}} = \sum_k w_k^2\left(\frac{s_{T,k}^2}{n_{T,k}} + \frac{s_{C,k}^2}{n_{C,k}}\right),
\qquad w_k = \frac{N_k}{N}
$$

   Báo `ValueError` nếu một tầng có dưới 2 đơn vị ở một nhánh (không tính được variance).

## Tiêu chí đạt

- Quantile strata chia đều; assignment cân bằng trong từng tầng, tái lập được với cùng seed, và mỗi
  đơn vị vào treatment khoảng 50% số lần qua nhiều seed.
- Với một tầng duy nhất, post-stratification trùng ước lượng Welch thông thường.
- Ví dụ tính tay trong test cho đúng `diff` và `se`.
- Qua 300 thí nghiệm mô phỏng (random đơn giản, không chia tầng lúc gán), ước lượng
  post-stratified không lệch, độ lệch chuẩn dưới 0.4 lần hiệu trung bình thông thường, CI 95% chứa
  giá trị thật 91–99% số lần.

## Gợi ý

### Gợi ý 1

`pd.qcut(x, q, labels=False)` cho nhãn quantile. Với `stratified_assign`: lặp qua từng tầng,
`rng.permutation` chỉ số trong tầng, gán xen kẽ True/False, và bốc ngẫu nhiên nhánh nào nhận vị
trí đầu tiên.

### Gợi ý 2

`df.groupby(["s", "t"]).y.agg(["mean", "var", "size"]).unstack("t")` cho một bảng mỗi tầng một
dòng, cột tách theo nhánh. `var` của pandas mặc định ddof=1. Ô thiếu (tầng không có đơn vị ở một
nhánh) hiện thành `NaN`.
