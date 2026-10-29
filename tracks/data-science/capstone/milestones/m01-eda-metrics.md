# M01: EDA và định nghĩa metric

## Mục tiêu

Dựng bảng một dòng mỗi đơn mà mọi milestone sau dùng lại, viết định nghĩa metric đủ chính xác để hai
người tính ra cùng một con số, và trả lời câu hỏi đầu tiên của Giám đốc Vận hành: **"Vì sao review xấu
tăng vọt đầu năm 2018, và nên làm gì?"** bằng một memo một trang.

Milestone này nối tiếp bài `modules/09-eda-storytelling/exercises/advanced/01-olist-eda-memo`. Nếu đã
làm bài đó, bạn dùng lại `order_table`, `rate_by`, `decompose_change` và mở rộng thêm phần metric.

## Việc cần làm

1. **Bảng `orders_cx`** trong `project/src/olist_cx/tables.py`: một dòng mỗi đơn giao xong, theo định
   nghĩa dùng chung trong README capstone (`tracks/data-science/capstone/README.md`). Giữ cả đơn không có review (cột `has_review`)
   để đo độ phủ review. Cột tối thiểu: `order_id`, `customer_unique_id`, `purchase_ts`, `carrier_ts`,
   `delivered_ts`, `estimated_ts`, `customer_state`, bang seller của item `order_item_id == 1`,
   `n_items`, `n_sellers`, `price`, `freight`, `promised_days`, `handling_days`, `delivery_days`,
   `late`, `late_days`, `review_score`, `bad_review`, `review_answer_ts`. Số ngày là số thực:
   `(a - b) / pd.Timedelta(days=1)`.
2. **Test cho bảng** trong `project/tests/test_tables.py` trên vài đơn tự dựng: đơn huỷ bị loại, đơn
   hai review lấy review trả lời sau cùng, đơn giao trong ngày hẹn nhưng sau giờ hẹn tính là trễ.
3. **Báo cáo chất lượng dữ liệu** (mục đầu notebook `notebooks/m01_eda.ipynb`): số đơn qua từng bước
   lọc, tỉ lệ đơn có review theo trễ / đúng hẹn, đơn có nhiều review, review được tạo **trước** ngày
   giao, đơn giao cho vận chuyển sau cả ngày hẹn, giá trị thiếu. Mỗi vấn đề ghi: ảnh hưởng tới metric
   nào, xử lý ra sao.
4. **Độ chín của nhãn**: đo khoảng thời gian từ lúc mua tới `review_answer_timestamp` (phân vị 50, 90,
   95, 99). Từ đó quy định: một tháng mua chỉ được báo cáo tỉ lệ review xấu sau bao nhiêu ngày.
5. **`reports/METRICS.md`**: cây metric với một OEC và các metric đầu vào, guardrail. Mỗi metric có:
   tên, công thức (tử số, mẫu số, đơn vị phân tích), mốc thời gian (theo ngày mua hay ngày giao), cửa
   sổ chờ nhãn chín, cách xử lý đơn không review, nguồn bảng, ai chịu trách nhiệm. Tối thiểu:
   - OEC: tỉ lệ review xấu trên đơn giao xong có review, theo tháng mua.
   - Đầu vào: tỉ lệ giao trễ, phân phối số ngày trễ, `promised_days`, `handling_days`.
   - Guardrail: tỉ lệ đơn có review (review là tự nguyện), số đơn giao xong mỗi tuần.
6. **Phân tích**: tỉ lệ review xấu theo tháng (bỏ tháng chưa chín); theo bang khách với khoảng Wilson
   và `min_n`; tách thay đổi tháng 1 → tháng 3/2018 thành phần mix và rate theo segment trễ / đúng hẹn:

   $$
   \Delta = \underbrace{\sum_s (w_{b,s} - w_{a,s})\, r_{a,s}}_{\text{mix}} + \underbrace{\sum_s w_{b,s}\,(r_{b,s} - r_{a,s})}_{\text{rate}}
   $$

   Kiểm tra Simpson khi so bang hoặc danh mục. Chọn 2–3 biểu đồ, mỗi biểu đồ có tiêu đề là kết luận.
7. **`reports/MEMO_EDA.md`** theo khung SCQA (Situation, Complication, Question, Answer), 250–700 từ,
   tiêu đề là kết luận có con số, có mục Giới hạn nói rõ phân tích này **chưa phải nhân quả** và bước
   tiếp theo để chắc chắn hơn (phân tích nhân quả ở M04, nếu bạn đã làm thì dẫn kết quả của nó).

Số tham chiếu để tự kiểm (Olist thật, bản cài đặt của người soạn):

| Con số | Giá trị |
| --- | --- |
| Đơn giao xong / có review | 96 470 / 95 824 (99.3%) |
| Tỉ lệ có review: đúng hẹn / trễ | 99.5% / 97.9% |
| Review xấu toàn bảng; ở đơn trễ / đúng hẹn | 12.8%; 54.1% / 9.2% |
| Review được tạo trước ngày giao | 8.5% đơn có review |
| Từ lúc mua tới lúc trả lời review, phân vị 95 | khoảng 31 ngày |
| Tháng 3/2018: review xấu / trễ | 21.2% / 21.1% |
| Tháng 1 → tháng 3/2018 | tổng +7.47 điểm, mix +7.69, rate −0.22 |
| Bang cao nhất / thấp nhất (min_n = 30) | AL 21.3% (394 đơn) / AP 6.1% (66 đơn) |

## Kết quả nộp

- `project/src/olist_cx/tables.py` và `project/tests/test_tables.py` (test xanh).
- `project/notebooks/m01_eda.ipynb` chạy được từ đầu tới cuối.
- `project/reports/METRICS.md` và `project/reports/MEMO_EDA.md`.

## Tiêu chí đạt

- [ ] Bảng `orders_cx` khớp số tham chiếu: 96 470 đơn giao xong, 95 824 có review, 12.8% review xấu.
- [ ] Test bảng xanh và bao được ba trường hợp: lọc trạng thái, nhiều review, trễ trong cùng ngày.
- [ ] Mỗi metric trong `METRICS.md` có đủ tử số, mẫu số, mốc thời gian, cửa sổ chín và cách xử lý đơn không review.
- [ ] Quy tắc "tháng chín" dựa trên phân phối đo được, không phải con số đoán.
- [ ] Biểu đồ theo bang có khoảng tin cậy; nhóm nhỏ không được trình bày như kết luận chắc chắn.
- [ ] Memo có tiêu đề là kết luận có số, nói được rằng gần như toàn bộ mức tăng đầu 2018 đến từ tỉ trọng đơn trễ (mix), và ghi rõ đây là tương quan (nếu đã làm M04, dẫn kết quả nhân quả ở đó).
