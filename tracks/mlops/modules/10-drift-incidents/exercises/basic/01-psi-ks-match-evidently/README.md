---
title: Tự cài PSI và KS khớp từng số với Evidently
level: basic
services: []
files:
  - path: starter/drift_metrics.py
    note: 4 hàm TODO
  - path: tests/test_match_evidently.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/10-drift-incidents/exercises/basic/01-psi-ks-match-evidently -q
---

## Mục tiêu

Hiểu rằng "PSI" không phải một con số duy nhất: mỗi công cụ chọn cách chia bin và cách xử lý bin rỗng khác nhau. Bạn cài lại đúng cách Evidently
tính, kiểm bằng cách so từng số với Evidently chạy thật, rồi thấy vì sao với mẫu lớn p-value của KS không còn là tín hiệu cảnh báo.

## Đề bài

Điền 4 hàm trong `starter/drift_metrics.py`. Test ghi hai khung dữ liệu ra Parquet rồi chạy `Report([DataDriftPreset(method=...)])` của Evidently (bản 0.7) trong container qua `mlopskit.evidently_python` (cần Docker; xem phần 0 của lý thuyết; thiếu Docker thì skip) trên cùng dữ liệu và yêu cầu
khớp tới sai số tương đối $$10^{-9}$$. Các luật dưới đây là toàn bộ những gì test ép; bạn không cần đọc mã Evidently.

- `psi(reference, current)`, hai đối số là Series hoặc mảng:
  1. Bỏ NaN ở từng tập trước khi làm gì khác; tỉ lệ (share) tính trên số dòng còn lại của tập đó.
  2. Nếu `reference` là kiểu số và có từ **21 giá trị khác nhau trở lên** thì chia bin số: biên bin là `np.histogram_bin_edges` của **hai tập nối lại** với `bins="sturges"` (bin rộng bằng nhau, không phải quantile). Ngược lại mỗi giá trị riêng là một bin, lấy hợp giá trị của hai tập (giá trị mới chỉ có ở `current` vẫn có bin).
  3. Bin rỗng xử lý bằng `_fill_zero_shares(shares)` (bên dưới), áp dụng riêng cho tỉ lệ của `reference` và của `current`.
  4. $$\mathrm{PSI} = \sum_i (r_i - c_i)\,\ln\frac{r_i}{c_i}$$ với $$r_i$$, $$c_i$$ là tỉ lệ của reference và current ở bin $$i$$. Trả `float`.
- `_fill_zero_shares(shares)`: nhận mảng tỉ lệ, trả **mảng mới** (không sửa mảng vào) trong đó mọi tỉ lệ bằng 0 được thay bằng `m / 1_000_000` nếu `m` (tỉ lệ khác 0 nhỏ nhất) không vượt `0.0001`, ngược lại bằng `0.0001`.
- `ks_pvalue(reference, current)`: p-value của `scipy.stats.ks_2samp`, bỏ NaN, trả `float`.
- `drift_flags(reference, current)`: dict có đúng 4 khoá: `psi`, `ks_p`, `psi_drift` (`psi >= 0.1`), `ks_drift` (`ks_p < 0.05`); hai cờ là `bool`.

Sau khi pass, đọc kết quả `test_large_sample_tiny_shift_is_significant_but_not_material`: 200 000 dòng mỗi tập, trung bình lệch 0.03 độ lệch chuẩn. KS báo drift có ý nghĩa thống kê nhưng PSI nói đó không phải drift đáng kể.
Test cuối dùng `trip_distance` thật của NYC TLC 2019-07 và 2019-12 (mẫu 50 000 dòng, `seed=0`; tự skip nếu chưa tải: `uv run python data/download_dataset.py nyc-tlc`).

## Tiêu chí đạt

- `psi` khớp Evidently trên cột Gauss có NaN, cột lệch phải, cột đuôi cực dài, cột số nguyên ít giá trị và cột chuỗi có giá trị mới lẫn NaN.
- `ks_pvalue` khớp Evidently trên bốn cột số.
- Hai mẫu giống hệt: PSI bằng 0 và p-value bằng 1.
- Quy tắc bin rỗng đúng cả hai nhánh (0.0001 và `m / 10**6`).
- Mẫu lớn lệch rất nhỏ: `ks_drift` là `True` còn `psi_drift` là `False`; lệch lớn: cả hai cờ `True`.
- Dữ liệu thật: PSI khớp Evidently và KS báo drift; trên `fare_amount` 2020-02 sang 2020-04 (mẫu 100 000 dòng, `seed=0`, đã lọc như bài notebook 01) PSI kiểu Evidently ≈ 0.005, thấp hơn nhiều so với PSI quantile ≈ 0.05.

## Gợi ý

### Gợi ý 1

`np.histogram(x, edges)[0] / len(x)` cho tỉ lệ từng bin; `np.concatenate([a, b])` để dựng biên chung. Cột chuỗi không có `is_numeric_dtype`, nên rơi vào nhánh mỗi giá trị một bin.

### Gợi ý 2

Với nhánh phân loại: `keys = set(reference.unique()) | set(current.unique())`, rồi đếm `(reference == k).sum()` cho từng khoá. Đừng quên bỏ NaN **trước** khi lấy `unique` và độ dài.
