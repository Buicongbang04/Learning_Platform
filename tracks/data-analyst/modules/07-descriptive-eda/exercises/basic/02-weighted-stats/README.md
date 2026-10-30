---
title: Thống kê có trọng số từ bảng tần suất và tỉ số - tự viết rồi so với pandas
level: basic
services: []
files:
  - path: starter/weighted_stats.ipynb
    note: 3 hàm TODO + so với pandas trên Telco và Rossmann
  - path: tests/test_weighted_stats.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py telco-churn
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-analyst/modules/07-descriptive-eda/exercises/basic/02-weighted-stats/starter/weighted_stats.ipynb
  - uv run pytest tracks/data-analyst/modules/07-descriptive-eda/exercises/basic/02-weighted-stats -q
---

## Mục tiêu

Tính được mean, độ lệch chuẩn và quantile khi mỗi dòng đại diện cho nhiều đơn vị (bảng tần suất, tỉ lệ của
nhóm, tỉ số của một cửa hàng-ngày), kiểm chúng khớp pandas/numpy, và biết trọng số nào trả lời câu hỏi nào.

## Đề bài

Team BI của nhà mạng không cho xuất dữ liệu từng khách, chỉ gửi bảng tần suất `tenure` → số khách. Finance cần
mean, SD, median và tứ phân vị của `tenure` từ bảng đó. Bộ `telco-churn` (7 043 khách) có dữ liệu gốc để bạn
kiểm lại; bộ `store-sales` (Rossmann) dùng cho câu hỏi "doanh số mỗi khách". Mở `starter/weighted_stats.ipynb`:

1. `weighted_mean(x, w) -> float`: bỏ cặp có NaN; `ValueError` nếu khác độ dài, có trọng số âm, hoặc tổng
   trọng số bằng 0.
2. `weighted_std(x, w, ddof=1) -> float`: SD với trọng số tần suất (chia cho tổng trọng số trừ `ddof`), khớp
   pandas `std()` (`ddof=1`) và `np.std` (`ddof=0`) trên dữ liệu đã nhân bản theo trọng số.
3. `weighted_quantile(x, w, q) -> float`: giá trị `x` đầu tiên có trọng số cộng dồn `>= q * tổng`, khớp
   `np.quantile(..., method="inverted_cdf")`; bỏ cặp có trọng số 0; `ValueError` nếu `q` ngoài `[0, 1]`.
4. Chạy các cell `explore`: so với dữ liệu gốc, so trung bình các tỉ lệ churn với tỉ lệ churn chung, và ba
   cách tính doanh số mỗi khách của Rossmann. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy
   notebook.

Các hàm nhận list, `np.ndarray` hoặc `pd.Series` và không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: khớp dữ liệu nhân bản theo trọng số, bỏ NaN, trọng số lẻ, kiểm
  lỗi đầu vào.
- Trên bộ thật: từ bảng tần suất `tenure` ra mean 32.37, SD 24.56, p25/median/p75 là 9/29/55 tháng; doanh số
  mỗi khách của Rossmann (trọng số theo số khách) 9.12 EUR, median theo số khách 8.86 EUR.
- Trắc nghiệm trong app: đúng ít nhất 5/7 câu.

## Gợi ý

### Gợi ý 1

Viết một hàm phụ `_pairs(x, w)` đổi cả hai sang `np.asarray(..., dtype=float)`, kiểm độ dài, bỏ NaN bằng mặt nạ
`~(np.isnan(x) | np.isnan(w))`, kiểm trọng số; ba hàm chính dùng chung nó. Đổi sang mảng numpy cũng giúp bỏ qua
index của `pd.Series` (hai Series khác index sẽ không bị căn hàng sai).

### Gợi ý 2

Quantile: `order = np.argsort(x)`, `cum = np.cumsum(w[order])`, rồi
`i = np.searchsorted(cum, q * cum[-1], side="left")`. `side="left"` trả vị trí đầu tiên có `cum >= q * tổng`.
