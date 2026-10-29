---
title: Chọn solver khi ma trận xấu điều kiện: normal equation, QR, SVD, ridge
level: advanced
services: []
files:
  - path: starter/solvers.py
    note: 6 hàm TODO
  - path: starter/REPORT.md
    note: Báo cáo cho tech lead
  - path: tests/test_solvers.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/01-math-for-ml/exercises/advanced/01-ill-conditioned-solvers -q
---

## Mục tiêu

Hiểu đủ sâu về numerical linear algebra để ra quyết định cho team: khi nào normal equation đủ
dùng, khi nào phải dùng QR hay SVD, khi nào vấn đề nằm ở feature chứ không ở solver. Đây là kiểu câu
hỏi "vì sao model ra hệ số 10¹³" mà DS senior được gọi vào để gỡ.

## Đề bài

1. Cài các hàm trong `starter/solvers.py`: `polynomial_features`, `solve_normal`, `solve_qr`,
   `solve_svd` (có ngưỡng `rcond`), `ridge` (không phạt intercept), `scaled_condition_number`
   (condition number sau khi chia mỗi cột cho chuẩn của nó).
2. Thí nghiệm có kiểm soát: dựng bài toán có condition number tăng dần (gợi ý: Vandermonde bậc 6
   tới 12 trên [0, 1], `y = X @ w_true` để biết đáp án), đo sai số của từng solver.
3. Olist thật, hai tình huống trên tập train (đơn mua trước 2018-01-01):
   - Feature đa thức trên **đơn vị gốc**: `[1, gram, cm³, gram², cm⁶, gram·cm³]`. Condition number bao
     nhiêu? Normal equation có thật sự sai không?
   - Một kỹ sư thêm cột **"peso cubado"** (khối lượng quy đổi của bưu điện Brazil: dài × rộng × cao /
     6000, đơn vị kg) cạnh thể tích. Mỗi solver trả gì?
4. Viết `starter/REPORT.md` theo khung có sẵn.

## Tiêu chí đạt

- Các test trong `tests/` pass, gồm: ba solver khớp nhau khi bài toán tốt; trên Vandermonde bậc 10
  (κ ≈ 2·10⁷) QR và SVD sai số dưới 1e-7 còn normal equation tệ hơn ít nhất 1000 lần (10 seed);
  SVD cho nghiệm min-norm khi thiếu hạng; ridge khớp `sklearn.linear_model.Ridge`; trên Olist thật,
  `solve_svd` chia hệ số giữa thể tích và peso cubado đúng như nghiệm min-norm.
- `REPORT.md` không còn TODO, có số liệu thật của bạn, phân biệt được ill-conditioning do đơn vị đo
  với do cột gần phụ thuộc tuyến tính.
- Chấm phần báo cáo theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Sai số tương đối của nghiệm khi giải một hệ có condition number κ bằng thuật toán ổn định cỡ
$$\kappa\cdot\varepsilon_{\text{machine}}$$ (với $$\varepsilon \approx 2.2\times10^{-16}$$). Normal equation giải hệ
$$X^\top X$$ có condition number $$\kappa^2$$. QR và SVD làm việc trực tiếp với $$X$$.

### Gợi ý 2

`np.linalg.qr` **không** pivot cột, nên không xử lý được ma trận thiếu hạng: bạn sẽ thấy hệ số
khổng lồ. `scipy.linalg.qr(X, pivoting=True)` hoặc `np.linalg.lstsq` (dùng SVD) thì xử lý được.
Với ridge không phạt intercept: giải $$(X^\top X + \lambda D)w = X^\top y$$ với $$D = \mathrm{diag}(0, 1, \dots, 1)$$.
