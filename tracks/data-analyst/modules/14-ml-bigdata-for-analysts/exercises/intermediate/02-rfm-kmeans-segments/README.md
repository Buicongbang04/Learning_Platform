---
title: K-means trên RFM Online Retail II - chia khách và đặt tên segment cho CRM
level: intermediate
services: []
files:
  - path: starter/rfm_kmeans.ipynb
    note: 5 hàm TODO + chọn k, hồ sơ cụm, đặt tên, kiểm độ ổn định
  - path: tests/test_rfm_kmeans.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/intermediate/02-rfm-kmeans-segments/starter/rfm_kmeans.ipynb
  - uv run pytest tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/intermediate/02-rfm-kmeans-segments -q
---

## Mục tiêu

Dùng k-means như DA dùng: dựng RFM đúng định nghĩa, đổi thang trước khi đo khoảng cách, chọn k theo cả số đo lẫn nhu cầu
kinh doanh, biến nhãn số thành tên segment có quy tắc giải thích được, và kiểm segment có ổn định không trước khi giao
cho đội CRM.

## Đề bài

Head of CRM cần 3–5 nhóm khách để thiết kế chương trình chăm sóc năm 2012 và hỏi mỗi nhóm bao nhiêu khách, mang bao nhiêu
doanh thu, nên gọi là gì. Dữ liệu: bộ `online-retail-ii`, sheet `Year 2010-2011`, dòng hợp lệ theo định nghĩa dùng
chung, chỉ khách có `Customer ID`, snapshot 2011-12-10. Mở `starter/rfm_kmeans.ipynb`:

1. `rfm_table(tx, snapshot)`: `recency` (ngày trọn tới snapshot), `frequency` (số hoá đơn), `monetary` (doanh thu gộp)
   theo `Customer ID`.
2. `prepare_features(rfm)`: `log1p` rồi chuẩn hoá từng cột (`ddof=0`).
3. `fit_kmeans(Z, k, seed=0)`: nhãn của `KMeans(n_clusters=k, n_init=10, random_state=seed)`.
4. `segment_profile(rfm, labels)`: `n`, `share`, `recency_median`, `frequency_median`, `monetary_median`, `revenue_share`
   theo cụm, sắp `monetary_median` giảm dần.
5. `name_segments(profile, rfm)`: `Champions`, `At risk`, `New / promising`, `Hibernating` theo quy tắc so median cụm
   với median chung (bảng trong notebook).
6. Chạy các cell `explore`: chọn k, thử k-means không đổi thang, hồ sơ k = 4, đổi seed để kiểm ổn định, scatter.

Cell đầu notebook đọc xlsx một lần (20-90 giây) rồi lưu bản parquet vào thư mục tạm của hệ điều hành. Báo cáo bài học:
làm phần trắc nghiệm trong app sau khi chạy notebook.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: RFM bỏ hoá đơn `C`, dòng giá 0, khách trống, recency là ngày trọn; đổi thang đúng; k-means
  tách hai cụm rõ; hồ sơ đúng cột và thứ tự; đặt tên đúng bốn trường hợp kể cả ở biên (`<=` và `>`).
- Trên bộ thật: 4 338 khách; khách 14646 có 280 206.02 GBP; median recency 50 ngày, frequency 2, monetary 674.49 GBP;
  k = 4 cho bốn cụm theo thứ tự `Champions`, `At risk`, `New / promising`, `Hibernating`, cỡ khoảng 713 / 1 187 / 812 /
  1 626 khách, cụm đầu mang khoảng 64.7% doanh thu.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`(snapshot - g["InvoiceDate"].max()).dt.days` cho ngày trọn (bỏ phần giờ). `log1p` (log của 1 + x) xử lý được
`recency = 0`. Chuẩn hoá bằng `(z - z.mean()) / z.std(ddof=0)`; pandas `std()` mặc định `ddof=1`.

### Gợi ý 2

`rfm.groupby(pd.Series(labels, index=rfm.index, name="segment"))` cho index tên `segment`. Khi so độ ổn định giữa hai
seed, đừng so nhãn số (cụm 0 ở lần chạy này có thể là cụm 2 ở lần khác): so **tên** đã đặt cho từng khách.
