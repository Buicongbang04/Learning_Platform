---
title: Gradient check bằng sai phân trung tâm
level: basic
services: []
files:
  - path: starter/gradcheck.py
    note: 2 hàm TODO
  - path: tests/test_gradcheck.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/basic/02-gradient-check -q
---

## Mục tiêu

Viết công cụ kiểm gradient mà cả module dùng lại: tính gradient số bằng sai phân trung tâm và so với
gradient giải tích bằng sai số tương đối. Có nó, mọi `backward` tự viết (bài 03, Intermediate) đều kiểm
được bằng một dòng thay vì tin vào mắt.

## Đề bài

**Phần cứng:** CPU · ~30 phút

Trong `starter/gradcheck.py`, viết:

1. `numerical_grad(f, x, eps=1e-6) -> ndarray`: `f` nhận một mảng cùng shape với `x` và trả về một số
   thực. Với từng phần tử $$x_i$$, ước lượng
   $$\frac{\partial f}{\partial x_i} \approx \frac{f(x + \varepsilon e_i) - f(x - \varepsilon e_i)}{2\varepsilon}$$,
   trong đó $$e_i$$ là vector đơn vị (chỉ phần tử $$i$$ dịch đi, mọi phần tử khác giữ nguyên). Kết quả cùng
   shape với `x`, `x` có thể nhiều chiều. **Sau khi hàm trả về, `x` phải giống hệt lúc gọi, từng bit.**
2. `relative_error(a, b) -> float`: đúng công thức ở mục 4 phần lý thuyết,
   $$\frac{\max_i |a_i - b_i|}{\max(\max_i |a_i| + \max_i |b_i|,\ 10^{-12})}$$, trả về `float` Python.

Chỉ dùng numpy trong `gradcheck.py`.

## Tiêu chí đạt

- `relative_error([1, 2], [1, 3]) == 0.2`; không đổi khi nhân cả hai mảng với cùng một hằng; hai mảng toàn 0 cho 0.
- Gradient số của $$\sum x^3$$ (x shape `(3, 4)`) và của log-sum-exp khớp gradient giải tích (và
  `torch.autograd`) với `rel < 1e-7`.
- `x` không đổi từng bit sau khi gọi `numerical_grad`.
- Mỗi lần gọi `f` chỉ đúng một phần tử khác `x` gốc, tổng cộng `2 * x.size` lần gọi.
- Tham số `eps` được dùng thật.
- Gradient sai 1% (nhân 1.01) cho `rel > 1e-3`: gradient check bắt được bug.

## Gợi ý

### Gợi ý 1

Duyệt mọi chỉ số của một mảng nhiều chiều mà không cần biết số chiều: `np.ndindex(x.shape)` trả lần
lượt các tuple chỉ số, dùng được trực tiếp làm `x[idx]`. Vì sao "từng bit" quan trọng: mục 4 lý thuyết,
bẫy "quên sửa lại tham số".

### Gợi ý 2

Trong vòng lặp, sửa `x` tại chỗ rồi gọi `f(x)` (không cần copy cả mảng mỗi lần). Đừng dịch và khôi
phục bằng chuỗi cộng trừ (`+= eps`, `-= 2 * eps`, `+= eps`): mỗi phép làm tròn một lần nên chưa chắc trả
đúng số cũ. Lưu giá trị gốc vào một biến trước khi dịch và gán lại đúng giá trị đó, kể cả khi `f` ném
lỗi (`try`/`finally`).
