---
title: Hiệu chỉnh multiple testing
level: intermediate
services: []
files:
  - path: starter/multiple.py
    note: 3 hàm TODO
  - path: tests/test_multiple.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/03-ab-testing/exercises/intermediate/02-multiple-testing -q
---

## Mục tiêu

Cài ba phương pháp hiệu chỉnh multiple testing và thấy bằng mô phỏng vì sao không hiệu chỉnh thì
"cứ nhìn đủ metric là kiểu gì cũng có cái thắng".

## Đề bài

Mỗi hàm trong `starter/multiple.py` nhận danh sách p-value (thứ tự bất kỳ, có thể trùng nhau) và
trả danh sách `bool` cùng thứ tự, `True` là bác bỏ H0:

1. `bonferroni(pvals, alpha=0.05)`: bác bỏ khi `p <= alpha / m`.
2. `holm(pvals, alpha=0.05)`: sắp p-value tăng dần; với p-value thứ k (đánh số từ 1), bác bỏ khi
   `p_(k) <= alpha / (m − k + 1)`; dừng ở lần đầu không bác bỏ được, mọi p-value sau đó đều không
   bị bác bỏ.
3. `benjamini_hochberg(pvals, alpha=0.05)`: sắp tăng dần, tìm k **lớn nhất** có
   `p_(k) <= k · alpha / m`, bác bỏ k p-value nhỏ nhất (kể cả những cái ở giữa không tự thoả).

Không dùng `statsmodels.stats.multitest` (test dùng nó để đối chiếu).

Mở rộng (không chấm): thí nghiệm Hillstrom có 2 nhánh email × 3 metric (`visit`, `conversion`,
`spend`) = 6 kiểm định. Tính p-value từng cặp bằng hàm của bài Basic 01, rồi áp ba phương pháp.
Kết luận có đổi không? Bài Advanced 01 dùng lại phần này.

## Tiêu chí đạt

- Kết quả trùng `statsmodels` cho cả ba phương pháp trên 5 vector p-value, gồm vector có giá trị
  trùng và không theo thứ tự, và với `alpha` khác 0.05.
- Holm bác bỏ mọi thứ Bonferroni bác bỏ (và có thể hơn).
- Mô phỏng 2 000 thí nghiệm 10 metric không có tác động: không hiệu chỉnh thì hơn 30% thí nghiệm có
  ít nhất một metric "có ý nghĩa"; với Holm thì không quá 6%.

## Gợi ý

### Gợi ý 1

`np.argsort(p, kind="stable")` cho thứ tự các chỉ số theo p tăng dần. Ghi kết quả vào một mảng
`reject` theo chỉ số gốc để giữ thứ tự đầu vào.

### Gợi ý 2

Benjamini-Hochberg là step-**up**: không dừng ở lần đầu thất bại như Holm. Tính mảng điều kiện
`sorted_p <= alpha * np.arange(1, m + 1) / m`, lấy vị trí `True` cuối cùng, bác bỏ mọi thứ tới vị
trí đó.
