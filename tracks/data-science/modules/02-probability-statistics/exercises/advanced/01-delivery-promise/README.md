---
title: Mô hình thời gian giao và chính sách ngày hẹn giao
level: advanced
services: []
files:
  - path: starter/fit.py
    note: fit_candidates, quantile_ci
  - path: starter/REPORT.md
    note: Đề xuất cho Vận hành
  - path: tests/test_fit.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/02-probability-statistics/exercises/advanced/01-delivery-promise -q
---

## Mục tiêu

Dùng phân phối xác suất để trả lời một câu hỏi kinh doanh thật: Olist nên hẹn khách ngày giao nào?
Hẹn quá xa thì khách bỏ giỏ hàng; hẹn quá gần thì giao trễ, và đơn trễ có tỉ lệ review xấu 54%. Bạn
fit nhiều họ phân phối bằng MLE, so bằng AIC, kiểm tra đuôi, ước lượng percentile kèm CI, rồi viết đề
xuất chính sách.

## Đề bài

1. `fit_candidates(x)` trong `starter/fit.py`: fit `expon`, `gamma`, `lognorm`, `weibull_min` (loc
   cố định 0), trả bảng `dist, loglik, n_params, aic, q95` sắp theo AIC.
2. `quantile_ci(x, q, n_boot=2000, seed=0, alpha=0.05) -> (estimate, lo, hi)`: percentile thực
   nghiệm và CI bootstrap, chia lô khi dữ liệu lớn.
3. Phân tích tự do trên Olist thật (notebook hoặc script của bạn): thời gian giao thực tế so với ngày
   hẹn (`order_estimated_delivery_date`), theo bang và theo thời gian; mô hình nào khớp **đuôi**; nếu
   hẹn theo percentile 90 hoặc 95 của từng bang thì ngày hẹn và tỉ lệ trễ thay đổi thế nào. Kiểm tra
   chính sách theo thời gian: ước lượng trên 2017, đánh giá trên 2018.
4. Viết `starter/REPORT.md` theo khung có sẵn.

AIC với k tham số và log-likelihood tại MLE là:

$$
\mathrm{AIC} = 2k - 2\log \hat L
$$

## Tiêu chí đạt

- `fit_candidates` đúng cấu trúc, AIC nhất quán với log-likelihood, chọn đúng họ phân phối trên dữ
  liệu mô phỏng (Lognormal, Weibull).
- `quantile_ci` đúng percentile, CI chứa percentile thật, tái lập theo seed.
- Trên Olist thật: Lognormal có AIC tốt nhất, nhưng q95 của nó (≈ 30.7 ngày) nằm trên CI của q95
  thực nghiệm (≈ 29.3 ngày).
- `REPORT.md` không còn TODO, ít nhất 300 từ.
- Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`dist.fit(x, floc=0)` trả tham số MLE (gồm cả loc = 0); `dist.logpdf(x, *params).sum()` là
log-likelihood; `dist.ppf(0.95, *params)` là q95. Số tham số được ước lượng là `len(params) - 1`.

### Gợi ý 2

AIC đo khớp **toàn bộ** phân phối, phần lớn khối lượng nằm quanh median. Chính sách ngày hẹn chỉ quan
tâm **đuôi phải** (p90, p95). Một mô hình có AIC tốt nhất vẫn có thể sai ở đuôi; một percentile thực
nghiệm với 96 nghìn đơn thì không cần mô hình. Mô hình hữu ích ở đâu? (Gợi ý: nhóm ít đơn, dự báo theo
đặc trưng của đơn.)
