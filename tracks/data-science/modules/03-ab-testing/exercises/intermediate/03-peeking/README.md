---
title: Peeking và biên O'Brien-Fleming bằng mô phỏng
level: intermediate
services: []
files:
  - path: starter/peeking.ipynb
    note: 4 hàm TODO
  - path: tests/test_peeking.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/data-science/modules/03-ab-testing/exercises/intermediate/03-peeking/starter/peeking.ipynb
  - uv run pytest tracks/data-science/modules/03-ab-testing/exercises/intermediate/03-peeking -q
---

## Mục tiêu

Tự thấy bằng mô phỏng vì sao "nhìn kết quả mỗi ngày và dừng khi p < 0.05" phá hỏng thí nghiệm, và
tự hiệu chỉnh một thiết kế group sequential cho phép nhìn nhiều lần mà vẫn giữ false positive 5%.

## Đề bài

Mở `starter/peeking.ipynb`. Mô hình mô phỏng được mô tả ở cell đầu: thí nghiệm A/A, giá trị
`Normal(0, 1)`, nhìn ở `n_looks` mốc cách đều, z-test với variance đã biết.

1. `z_at_looks(n_per_group, n_looks, n_sims, seed=0) -> np.ndarray` shape `(n_sims, n_looks)`.
   Vector hoá bằng `cumsum`; không lặp Python qua từng thí nghiệm.
2. `peeking_fpr(n_per_group, n_looks, n_sims, alpha=0.05, seed=0) -> float`: tỉ lệ thí nghiệm có
   **ít nhất một** lần nhìn với p < alpha.
3. `obf_fpr(c, n_per_group, n_looks, n_sims, seed=0) -> float`: như trên nhưng lần nhìn thứ k bác
   bỏ khi `|z_k| > c · sqrt(n_looks / k)`.
4. `calibrate_obf_constant(n_looks, alpha=0.05, n_sims=20000, seed=0) -> float`: tìm `c` để
   `obf_fpr` bằng alpha (dùng `n_per_group=100`).

Chạy các cell `explore` để xem false positive tăng theo số lần nhìn và đường p-value "chạm 0.05
rồi quay lại", rồi trả lời hai câu hỏi ở cuối notebook.

## Tiêu chí đạt

- Nhìn 1 lần: false positive 4–6%. Nhìn 10 lần: trên 12%. Càng nhìn nhiều càng tăng.
- Cùng seed cho cùng kết quả.
- O'Brien-Fleming với c = 1.96 cho false positive trên 5%; với c rất lớn thì không bao giờ bác bỏ.
- `calibrate_obf_constant(5)` trong khoảng 1.99–2.09 (giá trị trong sách: 2.040), và false positive
  tại c đó trên mô phỏng độc lập (seed khác) nằm trong 4–6%.
- Cả bài chạy dưới 20 giây.

## Gợi ý

### Gợi ý 1

`a = rng.standard_normal((n_sims, n_per_group)).cumsum(axis=1)`; tổng của `n_k` quan sát đầu là
cột `n_k − 1`. Mean = tổng / `n_k`. Lấy nhiều cột một lúc bằng chỉ số mảng: `a[:, n_k − 1]` với
`n_k` là mảng.

### Gợi ý 2

Thí nghiệm bị bác bỏ ⇔ `max_k |z_k| / sqrt(K/k) > c`. Vậy chỉ cần mô phỏng **một lần**, tính
`max_k |z_k| / sqrt(K/k)` cho mỗi thí nghiệm, và `c` chính là phân vị `1 − alpha` của nó (hoặc giải
bằng `brentq`). Không cần mô phỏng lại cho mỗi giá trị `c` thử.
