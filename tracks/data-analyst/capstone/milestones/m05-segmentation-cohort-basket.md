# M05: RFM, cohort retention, market basket, nhân khẩu học

## Mục tiêu

Trả lời câu hỏi "khách hàng nào tạo ra doanh thu và họ mua gì cùng nhau" bằng bốn góc nhìn, mỗi góc
kết thúc bằng một hành động marketing có thể làm: phân khúc RFM (tình huống 3), cohort retention, luật
kết hợp ở cấp commodity, và doanh thu theo nhóm nhân khẩu học (tình huống 5, thay cho địa lý). Điểm khó
của milestone này không nằm ở công thức mà ở chỗ **đọc kết quả đúng với bản chất của panel**: 2 500 hộ có
thẻ được theo dõi hai năm, không phải toàn bộ khách của chuỗi.

Kiến thức: module 12 (`12-product-customer-analytics`) mục 3 (cohort, retention), mục 5 (RFM), mục 6
(market basket). Bài gần nhất:
`modules/12-product-customer-analytics/exercises/intermediate/01-rfm-segments`,
`modules/12-product-customer-analytics/exercises/intermediate/02-market-basket-rules`,
`modules/12-product-customer-analytics/exercises/basic/02-cohort-heatmap-reading`,
`modules/12-product-customer-analytics/exercises/advanced/01-segment-winback-memo`.
Cohort bằng SQL đã gặp ở `modules/03-sql-for-analysts/exercises/intermediate/01-cohort-retention`.

## Việc cần làm

1. **RFM trên `household_key`** từ star schema: recency = 711 trừ `DAY` mua cuối, frequency = số basket,
   monetary = doanh thu ròng. Chấm điểm 1–5 theo quintile, đặt tên 5–7 phân khúc có ý nghĩa hành động
   (ví dụ Champions, At risk, Hibernating). Bảng mỗi phân khúc: số hộ, % doanh thu, AOV, recency trung vị.
   Hộ đã ngừng mua trong 8 tuần cuối là ứng viên "win-back": bao nhiêu hộ, đáng bao nhiêu doanh thu
   trước đây?
2. **Cohort retention theo "tháng" mua đầu** (4 tuần). Vẽ heatmap. Bạn sẽ thấy hai điều lạ: gần như mọi
   hộ "gia nhập" trong 5 tháng đầu, và retention gần như **phẳng** ở mức khoảng 80% thay vì giảm dần.
   Giải thích bằng cách panel được tuyển và giữ lại (hộ vào panel khi bắt đầu dùng thẻ được ghi nhận, không
   phải lúc trở thành khách mới). Kết luận: cohort ở đây đo **mức hoạt động đều đặn của panel**, không
   đo khả năng giữ khách mới; đề xuất metric thay thế (ví dụ tỷ lệ hộ hoạt động mỗi tháng, chi tiêu theo
   tháng thứ k của từng hộ).
3. **Market basket ở cấp `COMMODITY_DESC`** (cấp sản phẩm quá thưa). Loại `KIOSK-GAS`, `MISC SALES TRAN`,
   `MISC. TRANS.`, `COUPON/MISC ITEMS`, `NO COMMODITY DESCRIPTION` và chuỗi rỗng; transaction = basket.
   Chỉ xét commodity có support ≥ 1%; tính support, confidence, lift cho cặp (SQL tự join hoặc `mlxtend`).
   Trình bày hai bảng: cặp phổ biến nhất (support cao, lift thấp: "ai cũng mua") và cặp lift cao có support
   đủ lớn (cơ hội cross-sell, trưng bày cạnh nhau, coupon kèm). Một đoạn: lift cao không có nghĩa coupon cho
   món A sẽ làm tăng món B.
4. **Nhân khẩu học (tình huống 5)**. Doanh thu, số hộ, chi tiêu trung vị mỗi hộ, AOV theo `AGE_DESC`,
   `INCOME_DESC`, `HOUSEHOLD_SIZE_DESC`, `KID_CATEGORY_DESC`. Bắt buộc:
   - So sánh hộ **có** và **không có** nhân khẩu học trên chi tiêu và số basket. Nếu khác nhau lớn thì
     801 hộ này không đại diện cho 2 500 hộ; nói rõ hệ quả cho mọi kết luận theo nhân khẩu học.
   - Ghi cỡ nhóm cạnh mỗi con số; nhóm < 30 hộ không xếp hạng, gộp nhóm thu nhập nếu cần.
   - Phân biệt "nhóm X tiêu nhiều hơn" (mô tả) với "nhắm vào nhóm X sẽ tăng doanh thu" (chưa chứng minh).
5. **`reports/SEGMENTS.md`**: bốn mục trên, mỗi mục kết thúc bằng một khuyến nghị và cách đo khuyến nghị
   đó (gợi ý cho M06/M07: phân khúc nào nên được nhắm, metric nào theo dõi).

Số tham chiếu (dòng hợp lệ, bản cài đặt của người soạn):

| Đại lượng | Giá trị |
| --- | --- |
| Hộ mua đầu ở "tháng" 1 / 2 / 3 / 4 / 5 / sau đó | 447 / 521 / 616 / 681 / 223 / 12 |
| Retention cohort "tháng" 1 ở tháng +1 / +3 / +6 / +12 | 79,6% / 81,0% / 80,3% / 81,2% |
| Hộ không mua trong 4 tuần cuối / 8 tuần cuối (mua cuối ≤ ngày 683 / ≤ ngày 655) | 488 / 285 |
| Chi tiêu hai năm mỗi hộ: trung vị / trung bình | 2 158 / 3 223 |
| Basket dùng cho market basket / số commodity | 250 965 / 304 |
| Commodity phổ biến nhất | `SOFT DRINKS` 28,5% basket, `FLUID MILK PRODUCTS` 27,6% |
| Cặp support cao nhất | bánh mì (`BAKED BREAD/BUNS/ROLLS`) + sữa: support 12,34%, lift 1,86 |
| Cặp lift cao nhất (support ≥ 1%) | `DRY NOODLES/PASTA` + `PASTA SAUCE`: support 2,56%, confidence pasta → sauce 0,458, lift 9,81; `CHEESES` + `DELI MEATS`: lift 9,24 |
| Hộ có / không có nhân khẩu học: số hộ; chi tiêu trung vị; số basket trung vị | 801 / 1 699; 4 676 / 1 397; 139 / 52 |
| Nhóm thu nhập lớn nhất `50-74K`: số hộ; chi tiêu trung vị | 192; 4 980 |

Số market basket phụ thuộc đúng bộ lọc ở bước 3; đổi bộ lọc thì ghi lại và số sẽ khác.

## Kết quả nộp

- `project/notebooks/m05_segments.ipynb`, `project/sql/m05/*.sql`.
- `project/src/dunnhumby_da/segments.py` với ít nhất `rfm_scores(con) -> DataFrame` và
  `pair_rules(con, min_support) -> DataFrame`, có test trên fixture nhỏ tự tạo (vài basket) trong
  `project/tests/test_segments.py`.
- `project/reports/SEGMENTS.md`.

## Tiêu chí đạt

- [ ] RFM có tên phân khúc gắn hành động, bảng % doanh thu và số hộ win-back.
- [ ] Cohort heatmap được đọc đúng: giải thích việc nạp panel và retention phẳng, không kết luận "giữ khách tốt".
- [ ] Market basket ở cấp commodity, có bộ lọc ghi rõ, phân biệt cặp phổ biến với cặp lift cao, có khuyến nghị cross-sell thận trọng.
- [ ] Phân tích nhân khẩu học nêu chênh lệch hộ có/không có nhân khẩu học và cỡ nhóm cạnh mỗi số.
- [ ] Hàm `rfm_scores` và `pair_rules` có test chạy offline.
