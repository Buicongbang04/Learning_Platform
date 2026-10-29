---
title: "Dữ liệu cho dashboard KPI: tháng trống, kỳ chưa chín, tiêu đề kết luận"
level: intermediate
services: []
files:
  - path: starter/kpis.py
    note: 5 hàm TODO
  - path: tests/test_kpis.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/09-eda-storytelling/exercises/intermediate/03-kpi-dashboard-data -q
---

## Mục tiêu

Chuẩn bị đúng **dữ liệu đằng sau** một dashboard KPI theo tháng, nơi hầu hết lỗi trực quan hoá thật
sự xảy ra: tháng không có dữ liệu bị nối thẳng, tháng chưa chín làm đường "lao dốc", và tiêu đề chỉ
mô tả thay vì nói kết luận. Không cần nhìn biểu đồ để chấm: mọi quyết định nằm trong dữ liệu.

## Đề bài

Trong `starter/kpis.py`:

1. `monthly_kpis(orders, reviews, snapshot=None, maturity_days=30) -> DataFrame`: index là
   `PeriodIndex` theo tháng mua hàng, **đủ mọi tháng** từ tháng đầu tới tháng cuối (tháng không có
   đơn vẫn có dòng, `orders = 0`, tỉ lệ NaN). Cột `orders, delivered, late_rate, bad_review_rate,
   complete` theo docstring và định nghĩa dùng chung của track. `complete` là True khi thời điểm cuối
   tháng cộng `maturity_days` ngày không vượt `snapshot` (mặc định là lúc đặt đơn cuối cùng).
2. `latest_complete(kpis) -> Period`: tháng cuối cùng đã chín.
3. `headline(name, previous, current, kind="rate") -> str` theo **đúng** định dạng:

   | kind | Điều kiện | Kết quả |
   | --- | --- | --- |
   | `rate` | chênh lệch làm tròn 1 chữ số (điểm %) bằng 0 | `"{name} không đổi ở {current:.1%}"` |
   | `rate` | dương | `"{name} tăng từ {previous:.1%} lên {current:.1%} (+{điểm:.1f} điểm %)"` |
   | `rate` | âm | `"{name} giảm từ {previous:.1%} xuống {current:.1%} (-{abs(điểm):.1f} điểm %)"` |
   | `count` | % thay đổi làm tròn tới số nguyên bằng 0 | `"{name} không đổi ở {current}"` |
   | `count` | dương | `"{name} tăng {pct}% (từ {previous} lên {current})"` |
   | `count` | âm | `"{name} giảm {abs(pct)}% (từ {previous} xuống {current})"` |

   Số đếm in dạng số nguyên, ngăn cách hàng nghìn bằng dấu cách (`6 512`). `kind` khác thì
   `raise ValueError`.
4. `kpi_headline(kpis, column, name, kind="rate")`: `headline` cho tháng đã chín mới nhất so với
   tháng liền trước.

Sau khi xong, chạy trên Olist thật và trả lời: một line chart "số đơn theo tháng" vẽ thẳng từ
`groupby` sẽ sai ở những chỗ nào? Tiêu đề tự động cho tháng gần nhất là gì?

## Tiêu chí đạt

- Lưới tháng đầy đủ (tháng trống có dòng), `PeriodIndex`, đúng thứ tự cột.
- `delivered`, `late_rate` (giao 15:00 đúng ngày hẹn là trễ), `bad_review_rate` (review mới nhất,
  chỉ đơn giao xong có review) đúng trên dữ liệu nhỏ.
- `complete` đúng với snapshot mặc định và tuỳ chỉnh, cả `maturity_days = 0`.
- `headline` đúng từng ký tự ở cả sáu trường hợp; `kpi_headline` bỏ qua tháng chưa chín.
- Trên Olist thật: 26 tháng (2016-09 tới 2018-10, có 2016-11 trống), tổng 99 441 đơn và 96 470 đơn
  giao xong, tháng 3/2018 trễ 21.4% và review xấu 21.2%, tháng chín mới nhất là 2018-08, và
  `"Tỉ lệ giao trễ tăng từ 4.5% lên 10.4% (+5.9 điểm %)"`.

## Gợi ý

### Gợi ý 1

`pd.period_range(month.min(), month.max(), freq="M")` cho lưới; `value_counts().reindex(grid,
fill_value=0)` cho số đếm; `groupby(...).mean().reindex(grid)` cho tỉ lệ (để NaN, không điền 0: tháng
không có đơn không có tỉ lệ trễ 0%).

### Gợi ý 2

`grid.to_timestamp(how="end")` cho thời điểm cuối mỗi tháng (23:59:59.999… ngày cuối). Với
`headline`, làm tròn **trước** khi so với 0, để 8.01% → 8.03% ra "không đổi" chứ không ra "tăng 0.0
điểm".
