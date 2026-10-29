---
title: Delta method cho ratio metric
level: basic
services: []
files:
  - path: starter/ratio.py
    note: 4 hàm TODO
  - path: tests/test_ratio.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/04-advanced-experimentation/exercises/basic/02-delta-method -q
---

## Mục tiêu

Tính đúng sai số của một metric dạng "tổng trên tổng" (CTR, giá trung bình mỗi sản phẩm, doanh
thu mỗi phiên) khi đơn vị random là user, và thấy bằng mô phỏng cách tính "ngây thơ" làm báo động
nhầm nhiều cỡ nào.

## Đề bài

Dữ liệu ở cấp user: `num[i]` là số click của user `i`, `den[i]` là số lượt xem. Metric là
$$R = \sum_i \text{num}_i / \sum_i \text{den}_i$$. Trong `starter/ratio.py`:

1. `ratio_delta(num, den) -> (R, var_R)` theo delta method (công thức trong docstring và mục 5
   lý thuyết).
2. `naive_binomial_se(num, den)`: SE coi mỗi lượt xem là một phép thử Bernoulli độc lập. Hàm này
   **sai** khi cùng user có nhiều lượt xem; bạn viết nó để thấy nó sai thế nào.
3. `ratio_diff_ci(num_a, den_a, num_b, den_b, alpha=0.05) -> dict`: `diff`, `se`, `ci_low`,
   `ci_high`, `p_value` cho $$R_B - R_A$$.
4. `relative_lift_ci(...) -> dict`: `lift`, `se`, `ci_low`, `ci_high` cho $$R_B / R_A - 1$$. Đây là
   con số PM hay hỏi ("tăng bao nhiêu phần trăm").

## Tiêu chí đạt

- $$R$$ là tổng trên tổng, không phải trung bình các tỉ lệ của từng user.
- Khi `den` toàn 1, `var_R` đúng bằng variance của trung bình mẫu.
- SE delta method khớp bootstrap theo user trong 10%.
- Với click tương quan trong cùng user, SE ngây thơ nhỏ hơn 0.75 lần SE đúng.
- Qua 400 thí nghiệm A/A mô phỏng: delta method báo động nhầm khoảng 5% (2.5–8.5%), cách ngây thơ
  trên 15%.
- SE của `lift` khớp bootstrap trong 12%.

## Gợi ý

### Gợi ý 1

`np.cov(num, den)` trả ma trận 2×2: `[0, 0]` là var(num), `[1, 1]` là var(den), `[0, 1]` là
covariance, cùng ddof=1. Hai nhánh độc lập nên `se = sqrt(var_A + var_B)`.

### Gợi ý 2

Với `lift`, coi $$g(R_A, R_B) = R_B / R_A$$, đạo hàm riêng là $$-R_B / R_A^2$$ và $$1 / R_A$$. Delta
method: variance của $$g$$ là tổng bình phương đạo hàm nhân variance từng biến (hai nhánh độc lập
nên không có số hạng covariance).
