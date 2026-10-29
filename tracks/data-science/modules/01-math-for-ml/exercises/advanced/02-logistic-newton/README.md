---
title: Logistic regression từ đầu bằng gradient descent và Newton
level: advanced
services: []
files:
  - path: starter/logistic.ipynb
    note: 4 hàm TODO + phân tích tự do
  - path: starter/REPORT.md
    note: Báo cáo kỹ thuật
  - path: tests/test_logistic.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/01-math-for-ml/exercises/advanced/02-logistic-newton/starter/logistic.ipynb
  - uv run pytest tracks/data-science/modules/01-math-for-ml/exercises/advanced/02-logistic-newton -q
---

## Mục tiêu

Nối toàn bộ module: đạo hàm (gradient, Hessian qua chain rule), convexity, gradient descent so với
phương pháp bậc hai, condition number, regularization. Kết quả là một logistic regression tự viết
khớp `scikit-learn`, chạy trên câu hỏi thật của Olist: giao trễ ảnh hưởng thế nào tới review xấu.

## Đề bài

Mở `starter/logistic.ipynb`:

1. `build_review_table(orders, reviews)`: bảng một dòng mỗi đơn giao xong có review, cột `bad`,
   `late`, `delay_days`, `delivery_days`, `split`, theo **định nghĩa dùng chung** của track (ghi trong
   notebook).
2. `logistic_loss_grad_hess(w, X, y, l2)`: loss trung bình, gradient, Hessian, có L2 không phạt intercept.
3. `fit_logistic_gd` và `fit_logistic_newton`.
4. Phân tích tự do trong các cell `explore` và viết `starter/REPORT.md`:
   - tốc độ hội tụ hai optimizer trên dữ liệu thật, khi feature chuẩn hoá và khi để đơn vị gốc;
   - chi phí mỗi bước, và khi nào Newton không còn là lựa chọn (d lớn);
   - hệ số nói gì về giao trễ và review xấu; chất lượng trên val và test (chia theo thời gian);
   - convex vs non-convex: train một mạng nơ-ron nhỏ (vd. `MLPClassifier(hidden_layer_sizes=(8,))`)
     trên cùng feature với 10 seed, so loss và trọng số;
   - dữ liệu tách được hoàn toàn thì MLE ra sao, L2 giải quyết thế nào.

## Tiêu chí đạt

- Test pass: bảng dữ liệu đúng định nghĩa chung; gradient và Hessian khớp sai phân hữu hạn, Hessian
  nửa xác định dương; Newton khớp `LogisticRegression` (cả không phạt và có L2) trong ≤ 12 bước;
  gradient descent tới cùng optimum, chậm đi hơn 10 lần khi một feature bị nhân 10 còn Newton thì không;
  trên Olist thật 43 362 đơn train, hệ số khớp lời giải tham chiếu.
- `REPORT.md` không còn TODO; mọi con số lấy từ notebook của bạn.
- Chấm phần báo cáo theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Với $$p = \sigma(Xw)$$: gradient $$\frac{1}{n}X^\top(p - y)$$, Hessian $$\frac{1}{n}X^\top \mathrm{diag}(p(1-p))X$$.
Vì $$p(1-p) > 0$$ nên $$v^\top H v = \frac1n\sum_i p_i(1-p_i)(x_i^\top v)^2 \ge 0$$ với mọi $$v$$: loss lồi.
Newton: giải $$H\Delta = \nabla L$$ bằng `np.linalg.solve`, $$w \leftarrow w - \Delta$$.

### Gợi ý 2

Sklearn `LogisticRegression(C=C)` cực tiểu $$C\sum_i \ell_i + \tfrac12\lVert w\rVert^2$$ (không phạt
intercept). Chia cho $$Cn$$: tương đương loss trung bình cộng $$\tfrac{\lambda}{2}\lVert w\rVert^2$$ với
$$\lambda = 1/(Cn)$$. Không phạt: `C=np.inf`.
