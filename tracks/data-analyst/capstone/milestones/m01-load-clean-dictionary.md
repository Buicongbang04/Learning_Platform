# M01: Nạp dữ liệu, làm sạch, data dictionary

## Mục tiêu

Biến 8 tệp CSV của dunnhumby thành một database phân tích (DuckDB) mà mọi milestone sau dùng chung,
kèm hai tài liệu cho người đọc: **data dictionary** (mỗi bảng, mỗi cột nghĩa là gì, đã kiểm bằng dữ liệu
chưa) và **nhật ký làm sạch** (bỏ gì, giữ gì, bao nhiêu dòng, vì sao). Sau milestone này, câu "doanh thu
là bao nhiêu" chỉ có một câu trả lời trong cả dự án.

Kiến thức nằm ở module 06 (`06-data-cleaning`): mục 3 (dòng trùng theo khoá), mục 4 (outlier nghiệp vụ),
mục 6 (data quality check và nhật ký làm sạch), mục 7 (nghi ngờ dữ liệu). Bài gần nhất:
`modules/06-data-cleaning/exercises/basic/01-retail-cleaning-log` (log số dòng bị loại theo lý do) và
`modules/06-data-cleaning/exercises/advanced/01-store-sales-quality-report` (báo cáo chất lượng cho một bộ
mới). Cách nạp CSV vào database đã gặp ở `modules/05-data-collection/exercises/intermediate/02-retail-sqlite-load`.

## Việc cần làm

1. **Nạp**: viết `src/dunnhumby_da/load.py` tạo `artifacts/dunnhumby.duckdb` từ 7 bảng nhỏ bằng
   `read_csv` của DuckDB, ép kiểu tường minh (`BASKET_ID` và `COUPON_UPC` là `BIGINT`, các cột `*_DESC`
   là chuỗi). `causal_data.csv` (~696 MB) **không** nạp vào RAM bằng pandas: dùng DuckDB đọc thẳng CSV
   hoặc chuyển một lần sang Parquet; đặt `SET memory_limit` để máy yếu không treo. Chạy lại được: chạy hai
   lần cho cùng kết quả.
2. **Đối chiếu số dòng** với bảng "Con số tham chiếu" trong `capstone/README.md` (2 595 732 dòng giao dịch,
   276 484 basket, 2 500 hộ, 582 cửa hàng, tổng `SALES_VALUE` 8 057 463,08). Lệch thì dừng lại tìm lý do.
3. **Kiểm khoá và toàn vẹn** (mỗi kiểm là một câu SQL trả về số dòng vi phạm, mong đợi 0):
   - `product.PRODUCT_ID` duy nhất; mọi `PRODUCT_ID` trong giao dịch có trong `product`.
   - Một `BASKET_ID` chỉ thuộc một hộ, một ngày, một cửa hàng.
   - Dòng giao dịch trùng hoàn toàn.
   - Mọi hộ trong `campaign_table` có giao dịch; mọi dòng `coupon_redempt` khớp `coupon` theo
     (`COUPON_UPC`, `CAMPAIGN`) và khớp `campaign_table` theo (`household_key`, `CAMPAIGN`).
   - Khoảng ngày của campaign so với khoảng ngày của giao dịch.
4. **Dòng không hợp lệ cho doanh thu** theo định nghĩa dùng chung (`SALES_VALUE > 0` và `QUANTITY > 0`):
   đếm theo lý do (`SALES_VALUE = 0`; `SALES_VALUE > 0` nhưng `QUANTITY <= 0`), tổng tiền bị loại, số basket
   biến mất hoàn toàn sau khi lọc. Quyết định: lọc ở tầng nào (giữ dòng gốc trong bảng thô, lọc trong view
   phân tích) và ghi lại.
5. **Outlier nghiệp vụ**: `QUANTITY` có giá trị tới 89 638. Tìm xem các dòng `QUANTITY > 1000` thuộc
   ngành hàng nào, đoán ý nghĩa (gợi ý: xăng ở kiosk), và quyết định cách xử lý cho mọi phân tích "sản lượng"
   về sau. Kiểm cả các sản phẩm `COUPON/MISC ITEMS` và `NO COMMODITY DESCRIPTION`.
6. **`reports/DATA_DICTIONARY.md`**: mỗi bảng có grain ("một dòng là…"), khoá, số dòng; mỗi cột có kiểu,
   ý nghĩa, ví dụ giá trị, và cột "nguồn hiểu biết": *đã kiểm trên dữ liệu* hay *chỉ đoán từ tên cột*.
   Ghi lại cách bạn kiểm định nghĩa `SALES_VALUE` (net của `RETAIL_DISC` và `COUPON_MATCH_DISC`).
7. **`reports/CLEANING_LOG.md`**: bảng bước, số dòng trước/sau, số tiền bị loại, lý do; cuối có "giới hạn
   đã biết" (32% hộ có nhân khẩu học, `DAY` không phải ngày lịch, hai đầu thời gian bị cắt…).

Số tham chiếu (DuckDB trên CSV gốc, bản cài đặt của người soạn):

| Kiểm tra | Kết quả |
| --- | --- |
| Vi phạm khoá / toàn vẹn ở bước 3 | 0 cho mọi kiểm, trừ khoảng ngày campaign |
| Khoảng ngày campaign | `START_DAY` 224 .. `END_DAY` 719; một campaign (24, TypeB) kết thúc **sau** ngày 711 của giao dịch |
| Dòng `SALES_VALUE = 0` / `SALES_VALUE > 0` và `QUANTITY <= 0` | 18 850 / 67 (67 dòng này có tổng 19,28) |
| Sau lọc: số dòng / doanh thu ròng / số basket | 2 576 815 / 8 057 443,80 / 275 539 |
| Dòng `QUANTITY > 1000` | 23 101, **tất cả** thuộc `KIOSK-GAS` hoặc `MISC SALES TRAN` |
| `KIOSK-GAS`: tỷ trọng doanh thu / tỷ trọng tổng `QUANTITY` (dòng hợp lệ) | 6,8% / 84,9% |
| Sản phẩm có `DEPARTMENT` rỗng | 15 |

## Kết quả nộp

- `project/src/dunnhumby_da/load.py` và `project/sql/checks/*.sql` (mỗi tệp một kiểm tra).
- `project/notebooks/m01_load_clean.ipynb`: chạy kiểm tra, in bảng kết quả.
- `project/reports/DATA_DICTIONARY.md`, `project/reports/CLEANING_LOG.md`.
- `project/tests/test_load.py`: ít nhất kiểm số dòng sau nạp và "mọi kiểm toàn vẹn trả 0"; tự `skip` khi
  chưa có `data/raw/dunnhumby-complete-journey/`.

## Tiêu chí đạt

- [ ] Nạp lại từ đầu bằng một lệnh; không đọc `causal_data.csv` bằng pandas cả tệp.
- [ ] Số dòng, số basket, tổng `SALES_VALUE` khớp bảng tham chiếu của capstone README.
- [ ] Mỗi kiểm toàn vẹn là một câu SQL chạy lại được, có kết quả ghi trong log; phát hiện campaign kết thúc sau ngày 711.
- [ ] Nhật ký làm sạch cho biết số dòng và số tiền bị loại theo từng lý do, khớp 18 850 / 67 dòng.
- [ ] `QUANTITY` của xăng/giao dịch lặt vặt được nhận diện và có quyết định rõ cho các phân tích sản lượng.
- [ ] Data dictionary phân biệt "đã kiểm trên dữ liệu" với "đoán từ tên cột".
