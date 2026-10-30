---
title: Đọc kết quả A/B chiến dịch quảng cáo - SRM, cân bằng nhóm, khoảng tin cậy và quyết định
level: intermediate
services: []
files:
  - path: starter/ab_readout.ipynb
    note: 5 hàm TODO + ba câu cho CMO
  - path: tests/test_ab_readout.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py marketing-ab
  - uv run jupyter lab tracks/data-analyst/modules/11-stats-experimentation/exercises/intermediate/01-marketing-ab-readout/starter/ab_readout.ipynb
  - uv run pytest tracks/data-analyst/modules/11-stats-experimentation/exercises/intermediate/01-marketing-ab-readout -q
---

## Mục tiêu

Đọc một thí nghiệm thật theo đúng thứ tự của DA: kiểm tra độ tin cậy (SRM, cân bằng giữa hai nhóm) trước, rồi mới
ước lượng hiệu ứng có khoảng tin cậy, ra quyết định theo quy tắc đặt trước, và nói rõ điều dữ liệu không trả lời
được (correlation giữa số quảng cáo đã thấy và chuyển đổi không phải nhân quả).

## Đề bài

Bộ `marketing-ab` (Kaggle, CC0; tải cần Kaggle token, xem `data/README.md`): 588 101 người dùng, nhóm `ad` thấy
quảng cáo, nhóm `psa` thấy thông điệp công ích ở cùng vị trí; tỉ lệ chia thiết kế 96/4. CMO hỏi chiến dịch có
tạo thêm đơn không và có nên tiếp tục. Mở `starter/ab_readout.ipynb` (hàm `read_ab` đã viết sẵn):

1. `summarize(df)`: số người, số chuyển đổi, tỉ lệ mỗi nhóm.
2. `srm_check(observed, expected_share)`: chi-square goodness of fit với tỉ lệ thiết kế.
3. `segment_balance(df, segment)`: chi-square độc lập trên bảng `segment × group`.
4. `diff_ci(conv_t, n_t, conv_c, n_c, alpha)`: chênh lệch tỉ lệ, khoảng tin cậy Wald, p của z-test tỉ lệ gộp,
   lift tương đối.
5. `decide(ci_low, ci_high, mde, srm_ok, guardrail_ok)`: quy tắc quyết định 5 bước trong notebook.
6. Chạy các cell `explore`: SRM, tỉ lệ `psa` theo ngày, hiệu ứng tổng và theo ngày, chuyển đổi theo số quảng cáo
   đã thấy. Viết ba câu cho CMO. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: `srm_check` đúng công thức chi-square, nhận Series hoặc dict theo thứ tự bất kỳ;
  `diff_ci` khớp `proportions_ztest` của statsmodels và khoảng Wald; `decide` đúng 7 tình huống (gồm "có ý nghĩa
  nhưng nhỏ hơn MDE").
- Trên bộ thật: 564 577 / 23 524 người, 14 423 / 420 chuyển đổi; SRM so với 96/4 có p > 0.99; chênh lệch
  **+0.769 điểm %** [0.595; 0.943], tương đối **+43.1%**; bảng ngày × nhóm có chi2 = 235.6 (6 bậc tự do).
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`groupby("group").agg(users=("converted", "size"), conversions=("converted", "sum"))`. SRM:
`stats.chisquare(observed, expected)` với `expected = tỉ lệ * tổng quan sát`, lấy observed theo đúng thứ tự khoá
của `expected_share` (`pd.Series(observed).loc[list(expected_share)]`). Bảng chéo: `pd.crosstab(df[segment],
df["group"])` rồi `stats.chi2_contingency(table, correction=False)`.

### Gợi ý 2

Khoảng tin cậy dùng phương sai riêng của hai nhóm; p dùng tỉ lệ gộp (dưới H0 hai nhóm bằng nhau). Ngưỡng
`stats.norm.ppf(1 - alpha / 2)`, p hai phía `2 * stats.norm.sf(abs(z))`. Trong `decide`, thứ tự các điều kiện là
một phần của quy tắc: kiểm `ci_high < mde` **trước** `ci_low > 0`.

### Đọc thêm

Bài DS [03/basic/03-srm-check](../../../../../../data-science/modules/03-ab-testing/exercises/basic/03-srm-check/README.md)
đi sâu cơ chế gây SRM; bài này đặt SRM vào quy trình đọc kết quả và trả lời CMO.
