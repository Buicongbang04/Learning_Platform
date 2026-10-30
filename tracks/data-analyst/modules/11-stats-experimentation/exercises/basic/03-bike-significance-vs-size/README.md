---
title: Có ý nghĩa thống kê chưa phải là đáng kể - correlation và t-test trên Bike Sharing
level: basic
services: []
files:
  - path: starter/bike_tests.ipynb
    note: 4 hàm TODO + trả lời hai trưởng bộ phận
  - path: tests/test_bike_tests.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/11-stats-experimentation/exercises/basic/03-bike-significance-vs-size/starter/bike_tests.ipynb
  - uv run pytest tracks/data-analyst/modules/11-stats-experimentation/exercises/basic/03-bike-significance-vs-size -q
---

## Mục tiêu

Trả lời câu hỏi "có ảnh hưởng không" bằng **độ lớn kèm khoảng tin cậy** thay vì chỉ p-value: tự tính correlation
có khoảng tin cậy và Welch t-test, phân biệt "có ý nghĩa thống kê" với "đủ lớn để hành động", và thấy so sánh
không cùng mùa làm kết luận yếu đi thế nào.

## Đề bài

Bộ `bike-sharing-uci`, tệp `day.csv` (731 ngày 2011-2012). Trưởng vận hành hỏi độ ẩm "có ý nghĩa thống kê" thì có
nên giảm xe ngày ẩm; trưởng marketing hỏi ngày lễ có làm lượt thuê giảm. Mở `starter/bike_tests.ipynb`:

1. `to_business_units(day)`: thêm `temp_c`, `hum_pct`, `wind_kmh` theo hệ số trong Readme của UCI.
2. `corr_with_ci(x, y, alpha)`: Pearson r, khoảng tin cậy Fisher z, p hai phía, `n` (bỏ cặp thiếu).
3. `welch_compare(a, b, alpha)`: chênh lệch trung bình, khoảng tin cậy và p theo Welch.
4. `matched_holiday_gap(day, col)`: mỗi ngày lễ so với trung bình ngày làm việc cùng năm-tháng.
5. Chạy các cell `explore`: correlation ba biến thời tiết, ngày lễ so thẳng và so cùng tháng cho `cnt`,
   `casual`, `registered`. Trả lời 5 câu hỏi cuối notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau
   khi chạy notebook.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: `corr_with_ci` và `welch_compare` khớp `scipy` (r, p, khoảng tin cậy), bỏ cặp
  thiếu; `matched_holiday_gap` chỉ lấy ngày làm việc cùng tháng làm mốc; hàm không sửa đầu vào.
- Trên bộ thật: r(nhiệt độ, lượt thuê) = 0.627 [0.581; 0.670]; r(độ ẩm) = −0.101, p = 0.0065; ngày lễ so thẳng
  −850 lượt (p = 0.083), so cùng tháng −595 lượt; cả 21 ngày lễ đều có nhiều khách vãng lai hơn ngày làm việc
  cùng tháng.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`math.atanh`, `math.tanh`, `stats.norm.ppf(1 - alpha / 2)`; p của r: `2 * stats.t.sf(abs(t), df=n - 2)`. Bỏ cặp
thiếu: dựng `pd.DataFrame({"x": ..., "y": ...}).dropna()` bằng `np.asarray` để không phụ thuộc index của hai Series.

### Gợi ý 2

Welch: `va = a.var(ddof=1) / n_a`, tương tự `vb`; `se = sqrt(va + vb)`; bậc tự do theo công thức trong notebook;
`stats.t.ppf` cho ngưỡng và `stats.t.sf` cho p. Mốc cùng tháng:
`day[day.workingday == 1].groupby(["yr", "mnth"])[col].mean()` rồi `join(..., on=["yr", "mnth"])` vào các ngày lễ.

### Đọc thêm

Module 08 đã cho thấy ngày làm việc kéo `casual` và `registered` ngược chiều trên chart; bài này định lượng
chênh lệch đó cho ngày lễ kèm khoảng tin cậy. Lý thuyết kiểm định ở DS
[02-probability-statistics](../../../../../../data-science/modules/02-probability-statistics/README.md).
