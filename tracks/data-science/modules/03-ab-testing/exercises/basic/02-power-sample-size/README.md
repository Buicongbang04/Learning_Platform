---
title: Power, MDE và cỡ mẫu cho thí nghiệm
level: basic
services: []
files:
  - path: starter/power.py
    note: 3 hàm TODO
  - path: tests/test_power.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/03-ab-testing/exercises/basic/02-power-sample-size -q
---

## Mục tiêu

Tính được trước khi chạy thí nghiệm: cần bao nhiêu user, chạy bao lâu, và với lượng traffic có sẵn
thì tác động nhỏ nhất phát hiện được là bao nhiêu. Đây là câu hỏi đầu tiên trong mọi buổi review
thiết kế thí nghiệm.

## Đề bài

Thí nghiệm hai nhóm 50/50, kiểm định hai phía. Trong `starter/power.py`:

1. `sample_size_proportions(p_baseline, mde_abs, alpha=0.05, power=0.8) -> int`: số đơn vị
   **mỗi nhóm** để phát hiện tỉ lệ đổi từ `p_baseline` sang `p_baseline + mde_abs` (`mde_abs` có thể
   âm, ví dụ muốn *giảm* tỉ lệ review xấu). Dùng công thức trong mục 4 của lý thuyết, làm tròn lên.
2. `mde_proportions(p_baseline, n_per_group, alpha=0.05, power=0.8) -> float`: ngược lại, với số
   đơn vị mỗi nhóm cho trước, MDE dương nhỏ nhất phát hiện được. Giải số bằng `scipy.optimize.brentq`.
3. `sample_size_means(sigma, mde_abs, alpha=0.05, power=0.8) -> int`: cho metric liên tục có độ
   lệch chuẩn `sigma`.

Không dùng `statsmodels.stats.power` (test dùng nó để đối chiếu).

Sau khi xong, thử với baseline thật của Olist: tỉ lệ review 1–2 sao trên đơn đã giao là 12.8%,
khoảng 1 259 đơn giao mỗi tuần. Muốn phát hiện giảm 1 điểm phần trăm thì cần chạy bao nhiêu tuần?

## Tiêu chí đạt

- `sample_size_proportions(0.10, 0.01) == 14749` và `sample_size_proportions(0.128, -0.01) == 16930`.
- Cỡ mẫu giảm khi MDE tăng; MDE giảm một nửa thì cỡ mẫu tăng khoảng 4 lần.
- Tăng power hoặc giảm alpha thì cần nhiều mẫu hơn.
- `mde_proportions` là nghịch đảo của `sample_size_proportions`.
- Mô phỏng 3 000 thí nghiệm tại cỡ mẫu bạn tính cho tỉ lệ phát hiện trong khoảng 77–83%.
- `sample_size_means` lệch không quá 2% so với `statsmodels`.

## Gợi ý

### Gợi ý 1

`z = norm.ppf(1 - alpha / 2) + norm.ppf(power)`. Với α = 0.05, power = 0.8 thì z ≈ 1.96 + 0.84.
Viết một hàm phụ tính cỡ mẫu **chưa làm tròn**, để `mde_proportions` dùng lại.

### Gợi ý 2

`brentq(f, a, b)` tìm nghiệm của `f` trên `[a, b]` khi `f(a)` và `f(b)` trái dấu. Đặt
`f(m) = n_chưa_làm_tròn(p, m) − n_per_group`; chọn `a = 1e-6` (n rất lớn, f dương) và
`b = 1 − p_baseline − 1e-9` (n nhỏ, f âm).
