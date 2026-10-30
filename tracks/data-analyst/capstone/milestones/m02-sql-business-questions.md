# M02: Trả lời tình huống 1–4 bằng SQL

## Mục tiêu

Trả lời bốn tình huống đầu của đề "Phân tích dữ liệu bán hàng siêu thị" (xem bảng ánh xạ trong
`capstone/README.md`) bằng SQL chạy trên database của M01, kèm EDA đủ để người đọc tin con số. Mỗi câu
trả lời là **một câu SQL + một bảng/biểu đồ + một đến ba câu kết luận**, và mỗi kết luận nói rõ nó
đúng trong phạm vi nào.

Kiến thức: module 03 (`03-sql-for-analysts`) mục 3 (kỳ chưa đủ), mục 4 (top-N, Pareto), mục 6 (join nhân
bản dòng, reconcile); module 07 (`07-descriptive-eda`) mục 2–5 (mean vs median, phân phối lệch, trung bình
của trung bình) và mục 7 (EDA có câu hỏi). Các bài gần nhất:
`modules/03-sql-for-analysts/exercises/basic/01-monthly-revenue-mom`,
`modules/03-sql-for-analysts/exercises/basic/02-top-products-pareto`,
`modules/03-sql-for-analysts/exercises/intermediate/02-join-fanout-reconcile`,
`modules/03-sql-for-analysts/exercises/advanced/01-ceo-three-questions`,
`modules/07-descriptive-eda/exercises/intermediate/02-average-of-averages`,
`modules/07-descriptive-eda/exercises/advanced/01-store-eda-one-pager`,
`modules/07-descriptive-eda/exercises/advanced/02-revenue-concentration`.

## Việc cần làm

Mọi câu dùng view dòng hợp lệ của M01 và định nghĩa dùng chung. Mỗi câu SQL lưu thành một tệp trong
`sql/m02/`, có comment đầu tệp ghi câu hỏi business và grain kết quả.

1. **Tình huống 1: doanh thu theo thời gian.**
   - Doanh thu ròng theo `WEEK_NO` và theo "tháng" 4 tuần (`(WEEK_NO - 1) // 4 + 1`). Tuần 102 và "tháng"
     26 chỉ có một phần; tuần 1 chỉ có 5 ngày. Đánh dấu kỳ chưa đủ, không tính MoM cho chúng.
   - Doanh thu tăng mạnh ở năm "tháng" đầu. Trước khi gọi đó là tăng trưởng, đếm **số hộ đang có mặt**
     mỗi tuần và tuần mua đầu tiên của mỗi hộ. Viết một đoạn: đây là tăng trưởng kinh doanh hay là
     panel hộ gia đình đang được nạp dần? Chọn khoảng thời gian "ổn định" để báo cáo xu hướng.
   - Tỷ trọng doanh thu theo `DEPARTMENT` mỗi tháng (window function `SUM() OVER (PARTITION BY tháng)`);
     ngành nào đổi tỷ trọng nhiều nhất giữa nửa đầu và nửa sau giai đoạn ổn định.
2. **Tình huống 2: sản phẩm.**
   - Top-5 và bottom-5 sản phẩm theo doanh thu ròng (bottom chỉ xét sản phẩm có bán). Top-5 bị chiếm bởi
     `COUPON/MISC ITEMS` (xăng, giao dịch lặt vặt): báo cáo hai bảng, có và không có nhóm này, và nói vì sao.
   - `QUANTITY` vs doanh thu: tìm sản phẩm bán nhiều đơn vị nhưng doanh thu mỗi đơn vị thấp. **Loại**
     `KIOSK-GAS` và `MISC SALES TRAN` khỏi phân tích sản lượng (quyết định ở M01). Dùng thang log.
   - Thay cho `Class`: so sánh `BRAND` National với Private (tỷ trọng doanh thu, doanh thu mỗi đơn vị) và
     theo `DEPARTMENT`. Cẩn thận Simpson: so sánh trong từng ngành hàng, không chỉ trên tổng.
3. **Tình huống 3 (phần SQL): khách hàng.**
   - Repeat vs one-time theo định nghĩa chung. Kết quả gần như toàn bộ là repeat: nói thẳng điều đó, giải
     thích vì sao (panel khách có thẻ, theo dõi hai năm) và đề xuất một định nghĩa hữu ích hơn cho
     doanh nghiệp (ví dụ hộ còn hoạt động trong 4 hoặc 8 tuần cuối). Phân khúc sâu hơn để M05.
   - AOV và kích thước basket: mean và median giá trị basket, số dòng mỗi basket; histogram thang log.
4. **Tình huống 4: hiệu suất theo `STORE_ID`.**
   - Doanh thu, số basket, AOV mỗi cửa hàng. Phần lớn cửa hàng có rất ít basket: đặt ngưỡng quy mô tối
     thiểu (ghi rõ) trước khi xếp hạng; so với trung vị trong nhóm cùng quy mô, không so cửa hàng lớn với
     cửa hàng nhỏ.
   - Mức độ tập trung: top-10 và top-50 cửa hàng chiếm bao nhiêu % doanh thu (đường Pareto).
   - Độ ổn định: hệ số biến thiên (CV) doanh thu theo tuần cho các cửa hàng có doanh thu ở **mọi** tuần
     đủ (2..101). Lưu ý: cửa hàng ở đây là nơi các hộ trong panel mua, không phải toàn bộ doanh số cửa hàng.
5. **Reconcile**: tổng doanh thu theo tháng, theo ngành, theo cửa hàng đều phải bằng 8 057 443,80. Một
   câu join `product` làm lệch tổng là lỗi fan-out; ghi lại một câu kiểm như vậy.
6. **`reports/SQL_ANSWERS.md`**: mỗi tình huống một mục, mỗi mục có câu hỏi, link tệp SQL, bảng/biểu đồ,
   kết luận, giới hạn.

Số tham chiếu (dòng hợp lệ, bản cài đặt của người soạn):

| Đại lượng | Giá trị |
| --- | --- |
| Tuần 1 / tuần 102 | 5 ngày, 87 hộ / 6 ngày, 1 205 hộ |
| Hộ có tuần mua đầu ≤ 4 / ≤ 16; trung vị tuần mua đầu | 447 / 2 265; tuần 11 |
| Doanh thu "tháng" 1 / "tháng" 6 | 45 497 / 327 172 |
| Tỷ trọng: GROCERY / DRUG GM / PRODUCE / MEAT / KIOSK-GAS | 50,8% / 13,1% / 6,9% / 6,8% / 6,8% |
| Sản phẩm doanh thu cao nhất | 6534178 (`KIOSK-GAS`, `COUPON/MISC ITEMS`), 503 867 |
| Sản phẩm thường doanh thu cao nhất / có mặt ở nhiều basket nhất | 1029743 (sữa), 41 072 / 1082185 (trái cây nhiệt đới), 29 755 basket |
| National / Private (bỏ xăng và giao dịch lặt vặt): tỷ trọng doanh thu; doanh thu mỗi đơn vị | 78,6% / 21,4%; 2,42 / 1,67 |
| Hộ one-time / repeat | 3 / 2 497 |
| AOV / trung vị giá trị basket / trung vị số dòng mỗi basket | 29,24 / 17,18 / 5 |
| Cửa hàng có doanh thu / có ≥ 1 000 basket / có < 100 basket | 581 / 101 / 465 |
| Cửa hàng lớn nhất (367): tỷ trọng doanh thu | 3,3% |
| Top-10 / top-50 cửa hàng: tỷ trọng doanh thu | 19,4% / 64,1% |
| Cửa hàng có doanh thu ở cả 100 tuần đủ; trung vị CV doanh thu tuần | 68; 0,38 |

AOV ở đây (29,24) khác số trong capstone README (29,14) vì README tính trên mọi dòng, còn M02 lọc dòng
hợp lệ. Đây chính là loại chênh lệch cần ghi trong báo cáo.

## Kết quả nộp

- `project/sql/m02/*.sql` (mỗi câu hỏi một tệp).
- `project/notebooks/m02_sql_eda.ipynb`: chạy SQL qua DuckDB, vẽ biểu đồ.
- `project/reports/SQL_ANSWERS.md`.

## Tiêu chí đạt

- [ ] Kỳ chưa đủ (tuần 1, tuần 102, "tháng" 26) được đánh dấu và không dùng để kết luận tăng/giảm.
- [ ] Mức tăng đầu kỳ được giải thích bằng số hộ có mặt, không bị gọi là "tăng trưởng doanh thu".
- [ ] Top/bottom sản phẩm có bản loại `COUPON/MISC ITEMS`; phân tích sản lượng không dùng `QUANTITY` của xăng.
- [ ] So sánh National/Private có bản trong từng ngành hàng.
- [ ] Repeat vs one-time được nói rõ là gần như vô nghĩa trên panel này, kèm định nghĩa thay thế có số.
- [ ] Xếp hạng cửa hàng có ngưỡng quy mô và chuẩn hoá; có Pareto và CV.
- [ ] Mọi tổng hợp reconcile về cùng doanh thu ròng.
