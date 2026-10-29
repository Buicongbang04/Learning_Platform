---
title: Difference-in-Differences cho thuế thuốc lá California (Proposition 99)
level: basic
services: []
files:
  - path: starter/did.py
    note: 3 hàm TODO
  - path: tests/test_did.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py prop99
  - uv run pytest tracks/data-science/modules/06-causal-inference/exercises/basic/02-did-prop99 -q
---

## Mục tiêu

Cài DiD theo hai cách (bảng 2×2 và hồi quy two-way fixed effects), rồi tự kiểm tra giả định
parallel trends, thứ quyết định DiD có đáng tin hay không.

## Đề bài

Năm 1988 California thông qua Proposition 99: tăng thuế 25 cent mỗi bao thuốc và dùng tiền cho
chiến dịch chống hút thuốc, có hiệu lực từ 1989. Bộ `prop99` có `cigsale` (số bao bán trên đầu
người) của 39 bang, 1970–2000; 38 bang còn lại không có chương trình tương tự trong giai đoạn này.

Trong `starter/did.py`:

1. `did_2x2(df, outcome, treated, post) -> float`: hiệu của hai hiệu trung bình.
2. `did_regression(df, outcome, unit, time, treated, post) -> (coef, se)`: hồi quy
   `outcome ~ C(unit) + C(time) + treated:post` bằng `statsmodels`, standard error cluster theo
   `unit`.
3. `pretrend_slope_gap(df, outcome, time, treated, post) -> float`: trên giai đoạn trước can
   thiệp, nhóm treated dốc hơn nhóm control bao nhiêu mỗi năm (hệ số `time:treated` của
   `outcome ~ time * treated`).

Test tạo cột `treated` (California) và `post` (từ 1989) rồi gọi hàm của bạn.

## Tiêu chí đạt

- Đúng trên ví dụ 8 dòng tính tay và khớp `statsmodels` tới 1e-8.
- Trên panel mô phỏng có parallel trends, DiD tìm lại tác động −5 (sai số dưới 1); khi nhóm
  treated có trend dốc hơn 1 đơn vị mỗi năm, `pretrend_slope_gap` phát hiện được và DiD bị lệch.
- Trên dữ liệu thật: DiD ≈ −27.35 bao/người, SE cluster ≈ 2.85, pre-trend gap ≈ −1.23 bao/năm.

## Gợi ý

### Gợi ý 1

`df.groupby([treated, post])[outcome].mean()` trả Series có MultiIndex; lấy phần tử bằng
`m[1, 1]`, `m[0, 0]`... Trong hồi quy two-way fixed effects, fixed effect đơn vị hấp thụ cột
`treated` và fixed effect thời gian hấp thụ cột `post`, nên chỉ cần tương tác `treated:post`.

### Gợi ý 2

Tên cột là tham số, nên viết công thức bằng f-string: `f"{outcome} ~ C({unit}) + C({time}) + {treated}:{post}"`.
Cluster SE: `.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df[unit])[0]})`. Sau khi có
kết quả, hãy tự hỏi: SE cluster dựa trên giả định có nhiều cluster được can thiệp. Ở đây có mấy?
