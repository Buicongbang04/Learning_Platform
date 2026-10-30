---
title: Metric definitions YAML - hai báo cáo, một con số
level: intermediate
services: []
files:
  - path: starter/metrics.yml
    note: 4 metric TODO (revenue là mẫu)
  - path: starter/reports.py
    note: 3 hàm TODO
  - path: starter/metric_layer.py
    note: Có sẵn, không sửa
  - path: starter/legacy_reports.sql
    note: Hai truy vấn dashboard cũ để đọc, không chấm
  - path: tests/test_metrics.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run pytest tracks/data-analyst/modules/09-analytics-data-modeling/exercises/intermediate/02-metric-definitions -q
---

## Mục tiêu

Viết định nghĩa metric như một tài liệu sống (máy đọc được, người đọc hiểu được) và dựng hai báo cáo cho hai
team trên cùng định nghĩa, sao cho dòng **Tổng** của hai báo cáo luôn khớp nhau và đúng với metric non-additive.

## Đề bài

CFO thấy "doanh thu tháng 11/2011" là 1.46 triệu GBP trên dashboard Finance và 1.16 triệu trên dashboard
Marketing; AOV của Marketing là 18 GBP. Hai truy vấn cũ nằm trong `starter/legacy_reports.sql`: đọc để hiểu
vì sao lệch. Bạn thay chúng bằng một metric layer nhỏ:

- `starter/metric_layer.py` (có sẵn, không sửa): đọc `metrics.yml`, kiểm trường bắt buộc, sinh SQL trên bảng
  `fct_sales` (grain một dòng hàng hợp lệ; cột `line_id`, `invoice_no`, `invoice_month`, `country`,
  `customer_id`, `first_purchase_month`, `revenue`). Hàm `query(con, metrics, names, by=[...])` với dimension
  `month`, `country`, `customer_type`. Đọc docstring đầu tệp.
- `starter/metrics.yml`: `revenue` đã viết làm mẫu. Viết `orders`, `active_customers`, `new_customers`, `aov`:
  `description` cho người không biết SQL, `owner`, công thức (`type`, `expr`, `filters`, hoặc `numerator`/
  `denominator`), `additive_over_time` (cộng các tháng có ra con số của cả kỳ không), `caveats` (lưu ý thật của
  dữ liệu, ít nhất một dòng cho `active_customers`, `new_customers`, `aov`).
- `starter/reports.py`:
  1. `report(con, metrics, names, by)`: bảng chi tiết theo một dimension cộng dòng cuối `Tổng`, **tính lại từ
     metric layer** (không cộng hay lấy trung bình các dòng trên).
  2. `finance_monthly(con, metrics=None)`: `month`, `revenue`, `orders`, `aov`; tháng tăng dần.
  3. `marketing_country(con, metrics=None)`: `country`, `revenue`, `orders`, `active_customers`, `new_customers`,
     `aov`; sắp `revenue` giảm dần (hoà thì theo tên), dòng `Tổng` luôn cuối.

Test dựng `fct_sales` từ dữ liệu nhỏ sinh trong test và từ sheet `Year 2010-2011` thật. Làm xong, mở app làm phần
**Báo cáo bài học**.

## Tiêu chí đạt

- `metrics.yml` qua kiểm tra của metric layer; đủ 5 metric, không còn TODO, mô tả từ 30 ký tự, có owner;
  `additive_over_time` đúng cho cả 5; `aov` là ratio `revenue / orders`.
- Test trên dữ liệu nhỏ pass: số theo tháng và theo quốc gia; dòng `Tổng` của AOV khác trung bình các tháng; dòng
  `Tổng` của hai báo cáo bằng nhau.
- Trên bộ thật: 11/2011 doanh thu 1 509 496.33 GBP, 2 769 đơn, AOV 545.14; dòng Tổng 10 666 702.54 GBP, 19 960 đơn,
  AOV 534.40; United Kingdom 9 025 222.08 GBP, 3 920 khách; dòng Tổng 4 338 khách hoạt động, 4 338 khách mới, trong
  khi cộng các dòng quốc gia ra 4 346.
- Trắc nghiệm trong app (tuỳ chọn): đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

`new_customers`: đếm khách khác nhau, chỉ trên các dòng mà tháng hoá đơn bằng tháng mua đầu, tức
`filters: ["invoice_month = first_purchase_month"]`. Mỗi khách "mới" đúng một tháng, nên cộng các tháng ra số khách
của cả kỳ; `active_customers` thì không.

### Gợi ý 2

`report`: `detail = query(con, metrics, names, by=[by])`; `total = query(con, metrics, names).assign(**{by: TOTAL})`;
`pd.concat([detail, total[[by, *names]]], ignore_index=True)`. Ở `marketing_country`, sắp phần chi tiết
(`out.iloc[:-1]`) rồi nối lại dòng Tổng.
