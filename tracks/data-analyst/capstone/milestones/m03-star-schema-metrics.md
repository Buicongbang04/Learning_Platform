# M03: Star schema và định nghĩa metric dùng chung

## Mục tiêu

M02 trả lời đúng nhưng mỗi câu SQL tự join, tự lọc, tự định nghĩa doanh thu. Milestone này gom logic đó
vào **một star schema có grain rõ ràng và có test**, cộng một tệp `METRICS.md` là nguồn sự thật duy nhất
cho mọi metric. Dashboard (M04), phân khúc (M05), campaign (M06) và memo (M07) chỉ đọc từ đây, nên cùng một
câu hỏi luôn ra cùng một số.

Kiến thức: module 09 (`09-analytics-data-modeling`) mục 2 (grain), mục 3 (star schema), mục 4 (dbt),
mục 5 (data quality test), mục 6 (metric layer). Bài gần nhất:
`modules/09-analytics-data-modeling/exercises/basic/02-retail-star-schema`,
`modules/09-analytics-data-modeling/exercises/basic/03-fanout-revenue-audit`,
`modules/09-analytics-data-modeling/exercises/intermediate/01-dbt-retail-mart`,
`modules/09-analytics-data-modeling/exercises/intermediate/02-metric-definitions`,
`modules/09-analytics-data-modeling/exercises/advanced/02-grocery-schema-to-star`.

## Việc cần làm

1. **Thiết kế trên giấy trước** (mermaid `erDiagram` trong `reports/MODEL.md`), mỗi bảng một câu grain:
   - `fact_sales`: một dòng là **một sản phẩm trong một basket** (grain gốc của `transaction_data`). Cột đo:
     `sales_value`, `list_value` (giá niêm yết), `retail_disc`, `coupon_disc`, `coupon_match_disc`,
     `quantity`; cờ `is_valid_revenue` (định nghĩa dùng chung) và `is_fuel_or_misc` (M01).
   - `dim_product`: một dòng một `PRODUCT_ID`, chuẩn hoá chuỗi rỗng thành `UNKNOWN`.
   - `dim_household`: một dòng **cho mỗi hộ trong 2 500 hộ có giao dịch**, nhân khẩu học left join (hộ
     không có thì `has_demographic = false`, không bỏ hộ), cộng cờ `in_any_campaign`.
   - `dim_date`: một dòng một `DAY` (1..711): `week_no`, `month_4w`, `is_partial_week`,
     `is_partial_month`. Kiểm bằng dữ liệu công thức `WEEK_NO = (DAY + 1) // 7 + 1`; `DAY` không có thứ
     trong tuần thật, đừng tạo cột `weekday` như thể có.
   - `dim_store`: một dòng một `STORE_ID`, kèm nhóm quy mô dùng ở M02.
   - Tuỳ chọn cho M06: `fact_campaign_assignment` (hộ × campaign) và `fact_coupon_redemption`.
     Ghi rõ vì sao chúng là fact riêng chứ không gắn cột campaign vào `fact_sales` (hộ thuộc nhiều campaign
     cùng lúc, gắn vào sẽ nhân bản doanh thu).
2. **Xây** bằng dbt-duckdb (`dbt/models/staging`, `dbt/models/marts`) hoặc bằng các tệp SQL có thứ tự
   chạy rõ ràng; chọn một, ghi lý do trong `MODEL.md`.
3. **Test**: `unique` + `not_null` cho mọi khoá dimension; `relationships` từ fact sang mọi dimension;
   test tuỳ chỉnh: tổng `sales_value` của `fact_sales` bằng tổng `SALES_VALUE` của CSV gốc; số dòng
   `dim_household` = 2 500; `dim_date` đủ 711 ngày không hổng.
4. **Kiểm fan-out**: viết một câu "sai" join `fact_sales` với `fact_campaign_assignment` rồi cộng doanh
   thu, cho thấy tổng bị nhân lên bao nhiêu lần; đặt nó trong `MODEL.md` làm ví dụ cảnh báo.
5. **`reports/METRICS.md`**: mỗi metric một mục với tên, định nghĩa bằng lời, công thức SQL trên star
   schema, grain hợp lệ để cộng (ví dụ AOV **không** cộng được qua cửa hàng; phải tính lại từ tổng), bộ
   lọc mặc định, chủ sở hữu, và "hay bị hiểu nhầm là…". Tối thiểu: doanh thu ròng, doanh thu giá niêm yết,
   tỷ lệ giảm giá, số basket, AOV, số mặt hàng mỗi basket, hộ hoạt động (4 tuần), tỷ trọng ngành hàng,
   doanh thu mỗi hộ hoạt động, tỷ lệ dùng coupon (hộ dùng / hộ được gán).
6. **Chạy lại M02** trên star schema: mọi số tham chiếu của M02 phải ra y hệt. Không ra y hệt thì một
   trong hai bên sai; tìm và ghi lại.

## Kết quả nộp

- `project/dbt/` (hoặc `project/sql/model/`), chạy bằng một lệnh ghi trong `project/README.md`.
- `project/reports/MODEL.md` (ERD, grain, quyết định, ví dụ fan-out), `project/reports/METRICS.md`.
- `project/tests/test_model.py` hoặc `dbt test` xanh.

## Tiêu chí đạt

- [ ] Mỗi bảng có một câu grain và khoá; `dim_household` giữ đủ 2 500 hộ, nhân khẩu học là thuộc tính tuỳ chọn.
- [ ] `dim_date` dựa trên `DAY`, có cờ kỳ chưa đủ; không bịa ngày lịch hay thứ trong tuần.
- [ ] Test khoá, quan hệ và reconcile tổng doanh thu chạy xanh.
- [ ] Campaign không bị gắn thẳng vào `fact_sales`; có ví dụ fan-out định lượng.
- [ ] `METRICS.md` có công thức SQL, grain cộng được và lỗi hay gặp cho từng metric.
- [ ] Số M02 tái lập trên star schema không lệch.
