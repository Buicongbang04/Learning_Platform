---
title: Ước lượng đúng từ một khảo sát bị lệch
level: advanced
services: []
files:
  - path: starter/survey.py
    note: poststratified_mean, ipw_mean, poststrat_bootstrap_ci
  - path: starter/REPORT.md
    note: Báo cáo cho Trưởng CSKH
  - path: tests/test_survey.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/02-probability-statistics/exercises/advanced/02-biased-survey -q
---

## Mục tiêu

Sampling bias là lỗi thống kê gây hại nhiều nhất trong thực tế vì không có p-value nào báo động. Bài
này tái hiện một khảo sát lệch trên Olist thật, sửa nó bằng post-stratification và inverse probability
weighting, định lượng độ bất định, và viết rõ những gì không sửa được.

## Đề bài

Đội CSKH gọi điện khảo sát mức hài lòng. Khách có đơn trễ nghe máy nhiều hơn hẳn (đang chờ hàng, muốn
phàn nàn). Mô phỏng tình huống trên Olist thật: tổng thể là các đơn giao xong có review (định nghĩa
chung của track); "khảo sát" chọn mỗi đơn trễ với xác suất 0.5 và mỗi đơn đúng hẹn với xác suất 0.05
(`np.random.default_rng(0)`), "không hài lòng" là review xấu (score ≤ 2).

1. Trong `starter/survey.py`: `poststratified_mean`, `ipw_mean`, `poststrat_bootstrap_ci` theo docstring.
2. Phân tích tự do: tỉ lệ thô của khảo sát so với tổng thể; hiệu chỉnh theo trạng thái trễ; thử thêm
   tầng (vùng, category) và xem CI đổi thế nào; mô phỏng một cơ chế chọn mẫu **phụ thuộc chính mức
   hài lòng** (người không hài lòng nghe máy nhiều hơn, cùng trạng thái trễ) và cho thấy hiệu chỉnh
   theo trễ không sửa được.
3. Viết `starter/REPORT.md` theo khung.

Post-stratification với tỉ trọng tầng trong tổng thể là W_h:

$$
\hat\mu_{\text{post}} = \sum_h W_h\, \bar y_h,
\qquad
\hat\mu_{\text{IPW}} = \frac{\sum_i y_i / \pi_i}{\sum_i 1 / \pi_i}
$$

## Tiêu chí đạt

- `poststratified_mean` đúng công thức, chuẩn hoá tỉ trọng, báo `ValueError` khi thiếu tầng.
- Trên 10 tổng thể mô phỏng: trung bình thô lệch hơn 8 điểm phần trăm, post-stratification và IPW
  lệch dưới 2 điểm.
- CI bootstrap phân tầng chứa giá trị thật ở ít nhất 33/40 lần mô phỏng.
- Trên Olist thật: khảo sát thô cho trên 20% không hài lòng; hiệu chỉnh về 12.8% ± 1 điểm.
- `REPORT.md` không còn TODO, ít nhất 300 từ; phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`sample.groupby(strata)[y].mean()` cho trung bình từng tầng; `pop_shares / pop_shares.sum()` chuẩn hoá
tỉ trọng. So `set(shares.index)` với các tầng có trong mẫu để phát hiện tầng thiếu.

### Gợi ý 2

Bootstrap phân tầng: với mỗi tầng h có n_h quan sát, ma trận chỉ số `(n_boot, n_h)` cho trung bình
bootstrap của tầng; cộng `W_h ×` các trung bình đó qua các tầng là `n_boot` ước lượng. Resample cả mẫu
thay vì từng tầng sẽ làm số quan sát mỗi tầng dao động, thêm nhiễu không có trong thiết kế.
