---
title: "LaLonde: propensity score so với kết quả thí nghiệm"
level: intermediate
services: []
files:
  - path: starter/lalonde.ipynb
    note: 7 hàm TODO + phần kết luận
  - path: tests/test_lalonde.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py lalonde
  - uv run jupyter lab tracks/data-science/modules/06-causal-inference/exercises/intermediate/01-lalonde-propensity/starter/lalonde.ipynb
  - uv run pytest tracks/data-science/modules/06-causal-inference/exercises/intermediate/01-lalonde-propensity -q
---

## Mục tiêu

Làm lại thí nghiệm nổi tiếng nhất của causal inference: lấy một kết quả thí nghiệm ngẫu nhiên làm
chuẩn, vứt nhóm control ngẫu nhiên đi, thay bằng dữ liệu khảo sát, rồi xem propensity score
(IPW, matching) có tìm lại được con số thật không, và cái giá phải trả là gì.

## Đề bài

Chương trình đào tạo nghề NSW chia ngẫu nhiên người tham gia; tác động thật lên thu nhập năm 1978
là chênh lệch trung bình trên mẫu thí nghiệm: **$1 794**. Bộ quan sát ghép 185 người được đào tạo
với 2 490 người từ khảo sát PSID. Mở `starter/lalonde.ipynb`:

1. `diff_in_means(df, outcome="re78", treat="treat")`.
2. `smd(df, covariates, treat="treat", weights=None) -> Series`: standardized mean difference, có
   hỗ trợ trọng số (tử số có trọng số, mẫu số không trọng số).
3. `propensity_scores(df, covariates, treat="treat") -> ndarray`: logistic regression có hằng số,
   **không regularization**.
4. `att_weights(ps, treated)`, `ipw_att(df, ps, ...)`, `effective_sample_size(weights)`: IPW chuẩn
   hoá cho ATT.
5. `nn_match_att(df, ps, ...)`: 1-NN matching trên propensity score, có hoàn lại.
6. Chạy các cell `explore`: balance trước và sau khi cân, overlap, ESS, độ nhạy theo đặc tả và
   trimming. Viết kết luận 4–6 câu ở cell cuối.

## Tiêu chí đạt

- Mọi hàm đúng trên ví dụ nhỏ tính tay; propensity khớp `statsmodels.Logit` tới 1e-5.
- Trên dữ liệu mô phỏng có confounding (ATT ≠ ATE): IPW tìm lại ATT thật với sai số dưới 0.15 qua
  5 seed, sau khi cân |SMD| < 0.05; matching sai số dưới 0.25.
- Trên LaLonde thật: thí nghiệm $1 794.34; so sánh ngây thơ −$15 204.78; IPW với 8 covariate
  ≈ $1 759; matching ≈ $2 126; ESS của nhóm control ≈ 43.
- Kết luận nhắc tới overlap / ESS và độ nhạy theo đặc tả (chấm theo `SOLUTION.md`).

## Gợi ý

### Gợi ý 1

`sm.Logit(df[treat], sm.add_constant(df[covariates])).fit(disp=0)` rồi `.predict(X)`.
`LogisticRegression` của scikit-learn mặc định có regularization L2 (`C=1.0`) và biến thu nhập
không chuẩn hoá: propensity sẽ khác hẳn và test so với `statsmodels` sẽ fail.

### Gợi ý 2

Trọng số ATT "kéo" nhóm control về phân phối covariate của nhóm treated: người control có
propensity 0.5 đáng giá 1 người, có propensity 0.01 chỉ đáng 0.01 người. Nếu gần như mọi người
control đều có propensity rất nhỏ thì vài người còn lại gánh toàn bộ, và ESS cho biết "vài" là bao
nhiêu. Với matching: `np.abs(ps_t[:, None] - ps_c[None, :]).argmin(axis=1)` cho chỉ số người control
gần nhất của từng người treated (argmin lấy chỉ số đầu tiên khi hoà).
