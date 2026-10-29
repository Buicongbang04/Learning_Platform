---
title: Vector, phép chiếu và condition number
level: basic
services: []
files:
  - path: starter/linalg_basics.py
    note: 4 hàm TODO
  - path: tests/test_linalg_basics.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/01-math-for-ml/exercises/basic/01-vectors-projections -q
---

## Mục tiêu

Tự viết bốn phép toán nằm dưới mọi model tuyến tính: cosine similarity, chiếu một vector lên một
vector khác, ma trận chiếu lên không gian cột, và condition number. Làm xong bạn nhìn linear
regression như một phép chiếu hình học, và biết vì sao đơn vị đo ảnh hưởng tới độ ổn định số.

## Đề bài

Trong `starter/linalg_basics.py`:

1. `cosine_similarity(a, b) -> float`: cos góc giữa hai vector, $$\frac{a \cdot b}{\lVert a\rVert\,\lVert b\rVert}$$.
2. `project_onto_vector(v, u) -> ndarray`: hình chiếu vuông góc của `v` lên đường thẳng sinh bởi `u`.
3. `projection_matrix(X) -> ndarray`: ma trận $$P = X(X^\top X)^{-1}X^\top$$ (n×n) chiếu lên không gian
   cột của `X`. **Không** dùng `np.linalg.inv`: giải hệ $$(X^\top X)B = X^\top$$ bằng `np.linalg.solve`.
4. `condition_number(X) -> float`: $$\sigma_{\max}/\sigma_{\min}$$ từ singular value của `X`.

Test dùng ma trận thiết kế nhỏ giống bài phí ship Olist: cột hằng, khối lượng (kg), thể tích (lít).

## Tiêu chí đạt

- Cosine đúng trên các trường hợp vuông góc, cùng hướng, ngược hướng; không đổi khi nhân vector với hằng số.
- Phần dư `v − proj` vuông góc với `u`; chiếu hai lần bằng chiếu một lần.
- `P` đối xứng, `P @ P = P`, `trace(P)` bằng số cột, `P @ y` bằng giá trị dự đoán của least squares,
  và residual vuông góc với mọi cột của `X`.
- `condition_number` khớp `np.linalg.cond`; ma trận trực giao có condition number 1; đổi kg → g và
  lít → cm³ làm condition number tăng hơn 100 lần.

## Gợi ý

### Gợi ý 1

`np.linalg.solve(A, B)` chấp nhận `B` là ma trận: nó giải nhiều hệ cùng lúc, mỗi cột của `B` một hệ.
`np.linalg.solve(X.T @ X, X.T)` cho đúng $$(X^\top X)^{-1}X^\top$$ mà không phải tạo nghịch đảo.

### Gợi ý 2

`np.linalg.svd(X, compute_uv=False)` trả singular value đã sắp giảm dần. Ma trận `P` có kích thước
n×n: với n = 1 triệu dòng thì không bao giờ tạo nó trong thực tế; ở đây n = 200 để kiểm tính chất.
