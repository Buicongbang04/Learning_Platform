# Lời giải: cohort retention bằng SQL

> `starter/run_query.py` là helper để chạy thử SQL trên dữ liệu thật, không được chấm và không có bản lời giải: giữ nguyên.

## Cách làm

1. **`valid`** lọc dòng hợp lệ có `customer_id`. Cohort tính trên dòng hợp lệ, nên khách chỉ có hoá đơn huỷ
   hoặc dòng giá 0 chưa phải "đã mua".
2. **`last_complete`**: mốc từ dữ liệu. Ngày cuối 2011-12-09 không phải cuối tháng nên tháng đủ cuối là 11/2011.
3. **`first_month`**: `min(month)` theo khách trên **toàn bộ** dữ liệu (cả hai sheet). Chỉ đọc sheet
   2010-2011 thì mọi khách cũ mua tháng 12/2010 thành "khách mới".
4. **`activity`**: `SELECT DISTINCT customer_id, cohort_month, k`: grain "một khách active trong một tháng".
   Đếm dòng hoá đơn thay vì khách là lỗi fan-out quen thuộc: retention vượt 100%.
5. **Lưới `(cohort, k)`** bằng `generate_series` rồi `LEFT JOIN` số đếm: ô không ai quay lại vẫn có dòng 0.
   Heatmap thiếu ô thì người xem không phân biệt được "0" với "không có dữ liệu".
6. **Bảng wide**: `count(DISTINCT ...) FILTER (WHERE k = 3)` là pivot có điều kiện một lần quét (tương đương
   `SUM(CASE WHEN ...)` ở engine không có `FILTER`). Ô chưa quan sát được bọc trong `CASE WHEN cohort_month +
   INTERVAL k MONTH <= last_m THEN ... END` để thành `NULL`.

## Con số trên bộ thật

| Cohort | Cỡ | m1 | m3 | m6 | m12 |
| --- | --- | --- | --- | --- | --- |
| 12/2009 | 955 | 35.3% | 42.5% | 37.7% | 37.6% |
| 01/2010 | 383 | 20.6% | 30.6% | 25.9% | 22.2% |
| 11/2010 | 325 | 17.5% | 9.5% | 12.9% | 25.5% |
| 12/2010 | 76 | 9.2% | 9.2% | 5.3% | NULL |
| 03/2011 | 179 | 18.4% | 20.1% | 20.7% | NULL |
| 08/2011 | 106 | 27.4% | 26.4% | NULL | NULL |
| 10/2011 | 221 | 32.1% | NULL | NULL | NULL |
| 11/2011 | 191 | NULL | NULL | NULL | NULL |

24 cohort, tổng 5 850 khách (5 878 khách có mã trên toàn bộ dữ liệu; 28 khách mua lần đầu trong 1-9/12/2011 không
tạo cohort vì tháng chưa đủ).

## Đáp án trắc nghiệm

- **dec-cohort-size (c)**: **cắt trái (left-censoring)**. Dữ liệu bắt đầu 01/12/2009, nên mọi khách mua tháng
  12/2009 đều "mua lần đầu" trong dữ liệu, kể cả khách đã mua từ nhiều năm trước. Cohort 12/2009 thực chất là
  "mọi khách đang hoạt động", retention cao hơn hẳn các cohort khác (35% so với ~20%). Tháng 12/2010 có 885 khách
  có mã, nhưng 809 người đã mua trong năm trước nên chỉ 76 khách mới. Khi trình bày: tách riêng hoặc bỏ cohort
  đầu, và nói rõ các cohort đầu năm 2010 cũng còn lẫn khách cũ quay lại sau hơn một năm.
- **peak-k (a)**: k = 11 là tháng 11/2010, 49.5%: mùa đặt quà Giáng sinh của khách sỉ. Retention theo k trộn
  hiệu ứng "tuổi" của cohort với **mùa vụ** của tháng lịch; đọc theo đường chéo (cùng tháng lịch) để thấy mùa vụ.
- **oct-m1 (d)**: 32.1%. Cohort 10/2011 có m1 cao vì tháng 1 của nó là 11/2011, đúng cao điểm mùa vụ: chưa chắc
  khách mới gần đây "tốt hơn".
- **weighted-m1 (b)**: 23.5%. Trung bình có trọng số cao hơn vì cohort 12/2009 (955 khách, m1 35.3%) nặng nhất.
  Trung bình của các tỉ lệ khác tỉ lệ của tổng; chọn cái nào phụ thuộc câu hỏi ("một cohort điển hình" hay "một
  khách mới điển hình"), và cohort cắt trái nên bỏ khỏi cả hai.
- **null-vs-zero (a)**: `NULL` là "chưa tới lúc đo", `0` là "đo rồi, không ai quay lại". Trên heatmap, ô chưa
  quan sát được phải để trống.
- **distinct-activity (d)**: đếm dòng thay vì khách, retention có thể vượt 100%.
- **not-monotonic (b)**: định nghĩa của track là active **đúng** tháng k, không phải "còn sống tới tháng k"
  (unbounded retention: active ở tháng k hoặc bất kỳ tháng nào sau đó, luôn giảm dần). Hai định nghĩa đều đúng,
  phải ghi rõ đang dùng cái nào.
- **compare-cohorts (c)**: so cohort 03/2011 với cohort 03/2010 ở cùng k thì cùng tuổi và cùng mùa vụ; chỉ dùng ô
  đã quan sát được. So m12 thì chưa có cho cohort 2011; so theo tháng lịch trộn cohort tuổi khác nhau; trung
  bình mọi ô trộn k khác nhau và cohort 2011 có ít ô hơn.

## Sai lầm hay gặp

- Tính cohort trên một sheet, hoặc trên dữ liệu đã lọc theo kỳ báo cáo: khách cũ thành khách mới.
- Đưa tháng chưa đủ vào ma trận: cột cuối mọi cohort tụt xuống, trông như "khách bỏ đi hàng loạt".
- Pivot wide ngay trong truy vấn chính: khó nạp vào BI. Giữ bảng long làm nguồn, wide chỉ để trình bày.
