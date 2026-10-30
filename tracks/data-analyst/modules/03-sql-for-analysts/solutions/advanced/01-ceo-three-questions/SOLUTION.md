# Hướng làm: ba câu hỏi của CEO

> `starter/run_query.py` là helper để chạy thử SQL trên dữ liệu thật, không được chấm và không có bản lời giải: giữ nguyên.

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết ba truy vấn, con số tham chiếu trên bộ thật,
các quyết định cần cân nhắc, memo mẫu và rubric.

## Ba truy vấn

- **`q1_revenue_12m.sql`**: CTE `valid`; bảng kỳ `periods(period, start_date, end_date) AS (VALUES ...)`;
  `JOIN valid ON invoice_date >= start_date AND invoice_date < end_date`; `count(DISTINCT invoice)`,
  `count(DISTINCT customer_id)` (bỏ NULL tự động), `aov = sum / count(DISTINCT invoice)`. Sắp theo `start_date`.
- **`q2_new_vs_returning.sql`**: CTE `first_month` = `min(month)` theo khách trên **toàn bộ** dòng hợp lệ (không
  lọc kỳ); `LEFT JOIN` vào dòng hợp lệ, `CASE WHEN customer_id IS NULL THEN 'guest' WHEN first_month = month THEN
  'new' ELSE 'returning' END`; lọc tháng của `last_12m` **sau** khi đã gán loại; `count(DISTINCT customer_id)`
  cho ra 0 ở `guest`.
- **`q3_markets.sql`**: một CTE `valid` có cột `period` (`'prev'`/`'last'`), lọc trước 2011-12-01 và bỏ UK;
  `sum(revenue) FILTER (WHERE period = 'last')` cho từng kỳ; CTE thứ hai gom `(country, customer_id)` ở kỳ
  `last`, `max` theo nước; `growth = revenue_last / NULLIF(revenue_prev, 0) - 1`; `WHERE revenue_last IS NOT
  NULL ORDER BY revenue_last DESC LIMIT 10`.

Tự kiểm (reconcile): tổng `q2` qua 12 tháng = 754 193.58 + 7 639 021.53 + 1 634 676.75 = 10 027 891.86, đúng bằng
`last_12m` ở `q1`.

## Con số tham chiếu

| Câu | Con số |
| --- | --- |
| 1 | `prev_12m` 9 867 039.37 GBP, 20 117 đơn, 4 266 khách, AOV 490.48; `last_12m` **10 027 891.86** (+1.6%), 19 141 đơn (-4.8%), 4 297 khách (+0.7%), AOV **523.90** (+6.8%) |
| 2 | 12 tháng `last_12m`: returning 7 639 021.53 (**76.2%**), guest 1 634 676.75 (16.3%), new 754 193.58 (**7.5%**). Khách mới mỗi tháng 3-11% doanh thu (12/2010 thấp nhất 3.3%; 3/2011 và 6/2011 khoảng 11%). Tháng 11/2011: returning 1 080 557, guest 347 679 (cao bất thường), new 81 260 |
| 3 | EIRE 276 113 (-26.5%, 3 khách, khách lớn nhất 50%); Netherlands 273 718 (+1.9%, 9 khách, **98%** một khách); Germany 220 883 (+12.3%, 93 khách, 8%); France 202 438 (**+43.7%**, 86 khách, 9%); Australia 138 521 (+349%, 9 khách, **90%** một khách); Spain 61 261 (+30.9%, 29 khách); Switzerland 57 090 (+30.9%); Belgium 39 779 (+64.3%, 25 khách); Sweden 38 140 (-28.7%); Japan 37 416 (+567%, 8 khách) |

**Câu chuyện đúng**: tăng trưởng gần như đi ngang (+1.6%), giữ được nhờ giá trị đơn tăng trong khi số đơn giảm.
Doanh nghiệp sống nhờ khách cũ (76%); khách mới nhỏ và kỳ trước không đo được (xem quyết định 2). Ngoài UK, Germany
và France là thị trường thật (nhiều khách, không ai chiếm quá 10%, đang tăng); Netherlands, Australia, EIRE là vài
khách sỉ lớn, tăng giảm theo một hợp đồng.

## Các quyết định cần cân nhắc

1. **"Năm nay" là kỳ nào**: 2011 chưa hết. 12 tháng đủ gần nhất so với 12 tháng trước là so sánh công bằng nhất có
   thể; luỹ kế năm tới 9/12 (+3.8%, bài Basic 01) là cách khác, cũng chấp nhận được nếu nói rõ. So 2011 (chưa đủ)
   với 2010 (đủ) là sai.
2. **Khách mới ở kỳ trước bị cắt trái**: dữ liệu bắt đầu 12/2009 nên mọi khách của `prev_12m` đều "mới" trong
   tháng mua đầu của họ. Không so "khách mới năm nay vs năm ngoái" được; memo phải nói vậy thay vì báo "khách mới
   giảm 67%".
3. **Doanh thu gộp**: đơn mua rồi huỷ vẫn nằm trong doanh thu (ví dụ hoá đơn 74 215 hũ ngày 18/01/2011, 77 nghìn
   GBP, bị huỷ 16 phút sau). Với câu hỏi cấp năm, ảnh hưởng nhỏ nhưng phải ghi trong giới hạn.
4. **Độ tập trung trước tăng trưởng**: Australia +349% là một khách. Báo tăng trưởng không kèm số khách và tỉ trọng
   khách lớn nhất là mời CEO đầu tư vào một hợp đồng.
5. **Khách vãng lai**: 16% doanh thu không có mã khách, không biết mới hay cũ. Tháng 11/2011 guest tăng vọt
   (347 nghìn): đáng hỏi team vận hành (đổi cách ghi nhận, kênh mới) trước khi diễn giải.

## Memo mẫu (tóm tắt)

Headline: **"Doanh thu 12 tháng tăng 1.6% nhờ đơn lớn hơn; 76% đến từ khách quay lại; Germany và France là hai thị
trường nên mở rộng"**. Trả lời ngắn ba gạch đầu dòng như bảng trên; Câu 3 tách rõ "thị trường" (Germany, France)
khỏi "khách sỉ lớn" (Netherlands, Australia); Đề xuất: account manager cho khách sỉ lớn, thử thu hút khách sỉ mới ở
Germany/France đo bằng số khách mới mỗi tháng, thêm cờ đơn bị huỷ vào dashboard.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Kỳ và định nghĩa | 15 | Không so kỳ dở dang với kỳ đủ; nêu định nghĩa doanh thu, khách mới; nói rõ cắt trái ở kỳ trước |
| Câu 1 | 15 | Có mức tăng và tách được số đơn với AOV (hoặc khách × tần suất × AOV) |
| Câu 2 | 15 | Tỉ trọng ba loại khách có số; không so khách mới với kỳ bị cắt trái; nhắc 16% guest |
| Câu 3 | 20 | Xếp hạng có cả tăng trưởng, số khách, độ tập trung; chỉ ra ít nhất hai nước "một khách" |
| Reconcile | 10 | Có kiểm tổng `q2` = `q1` (hoặc tương đương) và ghi lại trong memo hoặc truy vấn kiểm |
| Memo | 20 | Headline trả lời thẳng; CEO không cần biết tên cột; mỗi số truy được về một truy vấn; đề xuất có người làm và mốc xem lại |
| SQL đọc được | 5 | CTE có tên nói lên ý nghĩa, định nghĩa dòng hợp lệ ở một chỗ, không gõ cứng con số |

Từ 70 điểm trở lên là memo gửi được trước buổi họp.

## Sai lầm hay gặp

- Tính "khách mới" chỉ trên dữ liệu đã lọc `last_12m`: mọi khách đều thành "mới" ở lần mua đầu trong kỳ.
- Đếm khách bằng `count(customer_id)`: ra số dòng có mã khách, không phải số khách.
- `growth_pct` chia cho 0 (nước mới) ra `inf` rồi đứng đầu bảng xếp hạng tăng trưởng.
- Memo liệt kê bảng số thay vì trả lời câu hỏi.
