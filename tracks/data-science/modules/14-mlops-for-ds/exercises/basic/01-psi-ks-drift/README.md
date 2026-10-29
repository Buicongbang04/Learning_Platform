---
title: Tự cài PSI và KS để đo data drift
level: basic
services: []
files:
  - path: starter/drift.py
    note: 4 hàm TODO
  - path: tests/test_drift.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/14-mlops-for-ds/exercises/basic/01-psi-ks-drift -q
---

## Mục tiêu

Tự cài hai thước đo drift phổ biến nhất (PSI và thống kê KS), hiểu từng quyết định nhỏ bên trong
(chia bin thế nào, bin rỗng xử lý ra sao, NaN đi đâu) và vì sao với dữ liệu lớn nên cảnh báo theo
**độ lớn** của drift chứ không theo p-value.

## Đề bài

Trong `starter/drift.py`:

1. `psi(expected, actual, bins=10, eps=1e-4) -> float`: PSI của mẫu hiện tại so với mẫu
   reference, đúng theo docstring: biên bin là quantile của `expected`, biên ngoài cùng là
   `-inf`/`+inf`, tỉ lệ mỗi bin chặn dưới bằng `eps`, bỏ NaN.
2. `psi_categorical(expected, actual, eps=1e-4) -> float`: mỗi giá trị là một bin, giá trị mới
   (chỉ có ở `actual`) và NaN đều được tính.
3. `ks_statistic(a, b) -> float`: tự cài bằng ECDF, không gọi scipy. Test so với
   `scipy.stats.ks_2samp`, kể cả khi dữ liệu có nhiều giá trị trùng.
4. `drift_level(psi_value) -> str`: `"stable"` (< 0.1), `"moderate"` (0.1 tới dưới 0.25),
   `"major"` (từ 0.25).

Công thức, với $$e_i$$ và $$a_i$$ là tỉ lệ của reference và mẫu hiện tại trong bin $$i$$:

$$
\mathrm{PSI} = \sum_i (a_i - e_i)\,\ln\frac{a_i}{e_i}
$$

Sau khi xong, chạy test dữ liệu thật: PSI của `delay_days` (số ngày giao trễ so với ngày hẹn) giữa
giai đoạn train và test của Olist. Con số đó nói gì, và vì sao KS p-value trên cùng dữ liệu gần
như bằng 0?

## Tiêu chí đạt

- Hai mẫu giống nhau cho PSI = 0; ví dụ tính tay 4 bin đúng tới 6 chữ số.
- PSI tăng theo độ lệch, đếm được giá trị nằm ngoài khoảng của reference, bỏ NaN, không lỗi khi
  dữ liệu gần như toàn giá trị trùng.
- PSI phân loại tính được giá trị mới xuất hiện và NaN.
- `ks_statistic` khớp scipy tới 1e-12.
- Mẫu 200 nghìn dòng lệch 0.03 độ lệch chuẩn: KS p-value < 0.001 nhưng PSI vẫn `"stable"`.
- Olist thật: PSI `delay_days` train → test ≈ 0.073, KS ≈ 0.0785 (tự skip nếu chưa tải).

## Gợi ý

### Gợi ý 1

`edges = np.unique(np.quantile(e, np.linspace(0, 1, bins + 1)))` rồi gán `edges[0] = -np.inf`,
`edges[-1] = np.inf`. `np.histogram(x, edges)[0] / len(x)` cho tỉ lệ mỗi bin. Nếu reference là
hằng số thì chỉ còn một biên: cần ít nhất hai biên để có một bin.

### Gợi ý 2

ECDF tại x là tỉ lệ giá trị nhỏ hơn hoặc bằng x: `np.searchsorted(sorted_a, x, side="right") / len(a)`.
Đánh giá cả hai ECDF tại mọi điểm của mẫu gộp rồi lấy max chênh lệch tuyệt đối. Với PSI phân loại:
`pd.Series(x, dtype=object).fillna("__missing__").value_counts(normalize=True)`.
