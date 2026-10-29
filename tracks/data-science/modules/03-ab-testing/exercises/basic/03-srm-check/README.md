---
title: Kiểm tra Sample Ratio Mismatch
level: basic
services: []
files:
  - path: starter/srm.py
    note: 2 hàm TODO
  - path: tests/test_srm.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cookie-cats
  - uv run pytest tracks/data-science/modules/03-ab-testing/exercises/basic/03-srm-check -q
---

## Mục tiêu

Cài kiểm tra SRM, phép kiểm tra chất lượng đầu tiên mà mọi experimentation platform chạy tự động
cho mọi thí nghiệm, và hiểu vì sao ngưỡng phải được chọn trước khi nhìn dữ liệu.

## Đề bài

Trong `starter/srm.py`:

1. `srm_pvalue(counts, expected_ratios) -> float`: chi-square goodness-of-fit giữa số đơn vị quan
   sát được ở mỗi nhánh và số kỳ vọng theo tỉ lệ thiết kế. `expected_ratios` cần được chuẩn hoá
   (`[1, 1]`, `[0.5, 0.5]`, `[50, 50]` là như nhau). Hỗ trợ 2 nhánh trở lên.
2. `has_srm(counts, expected_ratios, threshold=0.001) -> bool`.

Tự tính thống kê chi-square và dùng `scipy.stats.chi2` để lấy p-value; không dùng `scipy.stats.chisquare`.

Sau khi xong, chạy trên Cookie Cats thật (tải bằng lệnh ở trên): thí nghiệm thiết kế 50/50 nhưng
có 44 700 người ở `gate_30` và 45 489 người ở `gate_40`. Có SRM không? Câu trả lời phụ thuộc vào
điều gì?

## Tiêu chí đạt

- Chia đều tuyệt đối cho p = 1; Cookie Cats cho p ≈ 0.008608.
- Tỉ lệ thiết kế được chuẩn hoá; thiết kế 90/10 không lệch thì không báo SRM.
- Hoạt động với 3 nhánh.
- Trên 2 000 thí nghiệm A/A mô phỏng, tỉ lệ báo động ở ngưỡng 0.05 nằm trong 3.5–6.5%.
- Test trên dữ liệu thật Cookie Cats pass (tự skip nếu chưa tải).

## Gợi ý

### Gợi ý 1

`expected = observed.sum() * ratios / ratios.sum()`, rồi
`statistic = ((observed − expected)² / expected).sum()`.

### Gợi ý 2

p-value là xác suất phía phải của phân phối chi-square với `k − 1` bậc tự do (k là số nhánh):
`chi2.sf(statistic, df=k − 1)`. Nhớ trả `bool` thật (`bool(...)`), không phải `numpy.bool_`.
