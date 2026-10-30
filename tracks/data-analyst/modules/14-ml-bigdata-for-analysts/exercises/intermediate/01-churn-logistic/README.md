---
title: Logistic regression cho churn - đọc hệ số cho business và lift so với quy tắc
level: intermediate
services: []
files:
  - path: starter/churn_logit.ipynb
    note: 4 hàm TODO + đọc odds ratio, lift, so với quy tắc
  - path: tests/test_churn_logit.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py telco-churn
  - uv run jupyter lab tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/intermediate/01-churn-logistic/starter/churn_logit.ipynb
  - uv run pytest tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/intermediate/01-churn-logistic -q
---

## Mục tiêu

Dùng logistic regression theo cách DA dùng: chọn đặc trưng có nhóm tham chiếu và đơn vị dễ hiểu, đọc odds ratio kèm
khoảng tin cậy thành câu cho stakeholder, phân biệt tương quan với nguyên nhân, và đo giá trị của model bằng lift theo
decile so với quy tắc đang dùng ở cùng số cuộc gọi.

## Đề bài

Head of Retention hỏi: *"Yếu tố nào gắn với việc khách rời bỏ, mạnh cỡ nào?"* và *"Dùng model thay quy tắc
(month-to-month, gắn bó tối đa 12 tháng) thì đội gọi được lợi gì?"* Dữ liệu: bộ `telco-churn` (7 043 khách). Mở
`starter/churn_logit.ipynb`:

1. `build_features(raw)`: `X` gồm 10 cột theo bảng trong notebook (hằng `FEATURES`, nhóm tham chiếu month-to-month, DSL;
   `tenure_years`, `monthly_charges_10`), `y` là Series `int` tên `churned`. `split_data` đã viết sẵn (75/25, stratify,
   seed 42).
2. `fit_logit(X, y)`: `statsmodels` `Logit` có hệ số chặn, không regularization.
3. `odds_ratio_table(result)`: `coef`, `odds_ratio`, `ci_low`, `ci_high`, `p_value`, `odds_change_pct`; bỏ `const`, sắp
   `odds_ratio` tăng dần.
4. `decile_table(y_true, score, n_bins=10)`: `n`, `churners`, `rate`, `lift`, `cum_capture` theo nhóm điểm (1 = cao nhất),
   chia theo vị trí sau khi sắp ổn định giảm dần.
5. Chạy các cell `explore`: bảng odds ratio, ROC-AUC, bảng decile, so model với quy tắc ở cùng số khách được gọi, chart.

Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: đặc trưng đúng nhóm tham chiếu và đơn vị (kể cả `"No internet service"` không phải
  `"Yes"`), không sửa đầu vào; fit khớp `statsmodels` không regularization và tìm lại odds ratio thật trên dữ liệu
  sinh; bảng odds ratio đúng cột, bỏ `const`, đúng thứ tự; decile chia theo vị trí, hoà điểm giữ thứ tự.
- Trên bộ thật (train 5 282, test 1 761): odds ratio hợp đồng hai năm 0.251, mỗi năm gắn bó 0.684, cáp quang +95.4%
  odds; ROC-AUC test 0.8407; decile 1 có 130/177 khách rời (lift 2.77); ba decile đầu phủ 66.2% khách rời.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`sm.add_constant(X, has_constant="add")` thêm cột `const` kể cả khi `X` có cột hằng (dữ liệu nhỏ). `result.conf_int()`
trả DataFrame hai cột `0` và `1` theo thang hệ số; lấy `np.exp` cho cả hai để ra khoảng tin cậy của odds ratio.

### Gợi ý 2

`np.argsort(-score, kind="stable")` cho thứ tự giảm dần giữ nguyên thứ tự đầu vào khi hoà. Nhóm của vị trí `i` là
`i * n_bins // n + 1`; với 1 761 khách, nhóm 1 có 177 khách, các nhóm sau 176. Odds ratio của hai năm gắn bó là
odds ratio một năm **bình phương**, không phải nhân đôi phần trăm.
