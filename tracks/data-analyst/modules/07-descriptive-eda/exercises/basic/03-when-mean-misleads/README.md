---
title: Khi mean lừa - nhiều đỉnh, số 0, đuôi dài trên Telco và Rossmann
level: basic
services: []
files:
  - path: starter/mean_misleads.ipynb
    note: 4 hàm TODO + chọn con số để báo
  - path: tests/test_mean_misleads.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py telco-churn
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-analyst/modules/07-descriptive-eda/exercises/basic/03-when-mean-misleads/starter/mean_misleads.ipynb
  - uv run pytest tracks/data-analyst/modules/07-descriptive-eda/exercises/basic/03-when-mean-misleads -q
---

## Mục tiêu

Nhận ra ba kiểu mean không đại diện (phân phối nhiều đỉnh, số 0 trộn vào tập dòng, đuôi dài và vài giá trị cực
trị), đo được mức "lừa" bằng công cụ robust, và chọn đúng con số cho từng câu hỏi của stakeholder: con số điển
hình, con số theo nhóm, hay mean thật để cộng thành tổng.

## Đề bài

Dữ liệu: `telco-churn` (cột `MonthlyCharges`, `InternetService`) và `store-sales` (`train.csv` doanh số ngày,
`store.csv` cột `CompetitionDistance`). Mở `starter/mean_misleads.ipynb`:

1. `trimmed_mean(s, prop) -> float`: bỏ NaN, bỏ `floor(prop * n)` giá trị mỗi đầu (khớp
   `scipy.stats.trim_mean`); `ValueError` nếu `prop` ngoài `[0, 0.5)`.
2. `winsorized_mean(s, lower=0.05, upper=0.95) -> float`: bỏ NaN, kẹp giá trị vào hai phân vị (mặc định
   pandas), rồi lấy mean; `ValueError` nếu không có `0 <= lower < upper <= 1`.
3. `share_within(s, center, width) -> float`: tỉ lệ giá trị không NaN trong `[center - width, center + width]`.
4. `mean_without_top(s, k) -> float`: mean sau khi bỏ `k` giá trị lớn nhất; `ValueError` nếu `k < 0` hoặc
   `k >= n`.
5. Chạy các cell `explore`: cước tháng theo loại internet, doanh số ngày có và không có ngày đóng cửa, bảng "mean
   có đáng tin không" cho `CompetitionDistance` và doanh số trung bình mỗi cửa hàng. Trả lời ba câu hỏi ở phần 6
   của notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: số giá trị bị cắt, kẹp theo phân vị, tính cả hai đầu đoạn, kiểm
  lỗi đầu vào, bỏ NaN.
- Trên bộ thật: 7.6% khách có cước trong mean ± 5 USD (11.6% quanh median); `CompetitionDistance` có trimmed mean
  10% là 3 774.96 m, winsorized mean 5–95% là 4 932.89 m, mean khi bỏ 10 cửa hàng xa nhất là 5 020.34 m.
- Trắc nghiệm trong app: đúng ít nhất 5/7 câu.

## Gợi ý

### Gợi ý 1

Đổi về mảng đã sắp xếp một lần: `x = np.sort(pd.Series(s).dropna().to_numpy(dtype=float))`. Trimmed mean là
`x[k:len(x) - k].mean()`, mean bỏ top k là `x[:len(x) - k].mean()`. Cẩn thận với `k = 0`: `x[0:len(x)]` đúng,
nhưng `x[:-0]` là mảng rỗng.

### Gợi ý 2

`Series.between(a, b)` mặc định tính cả hai đầu. `Series.clip(lo, hi)` kẹp giá trị mà không đổi số quan sát.
