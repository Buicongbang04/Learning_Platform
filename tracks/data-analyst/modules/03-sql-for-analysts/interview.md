# Câu hỏi phỏng vấn: SQL cho Data Analyst

## Window function khác GROUP BY thế nào? Cho một ví dụ phải dùng window function.

`GROUP BY` **gộp** nhiều dòng thành một dòng mỗi nhóm; window function **giữ nguyên** từng dòng và gắn thêm một giá
trị tính trên "cửa sổ" các dòng liên quan (`PARTITION BY` chia nhóm, `ORDER BY` xếp thứ tự, frame chọn phạm vi).

Ví dụ phải dùng window: "tỉ trọng doanh thu của mỗi sản phẩm trong nước của nó". Cần cả doanh thu sản phẩm (grain
nước × sản phẩm) và tổng của nước trên **cùng một dòng**:

```sql
SELECT country, stock_code, revenue,
       revenue / sum(revenue) OVER (PARTITION BY country) AS share_of_country
FROM by_product
```

Với `GROUP BY` thì phải tính tổng nước trong một truy vấn con rồi join lại. Các bài DA hay gặp cần window: top-N
theo nhóm, MoM/YoY (`lag`), luỹ kế và Pareto (`sum ... OVER (ORDER BY ...)`), trung bình trượt, lấy bản ghi mới nhất
mỗi khách (`row_number() = 1`), chia phiên từ log sự kiện.

## Lấy top 3 sản phẩm theo doanh thu ở mỗi quốc gia. Chọn ROW_NUMBER, RANK hay DENSE_RANK?

```sql
WITH by_product AS (
    SELECT country, stock_code, sum(quantity * price) AS revenue
    FROM valid GROUP BY 1, 2
)
SELECT *, row_number() OVER (PARTITION BY country ORDER BY revenue DESC, stock_code) AS rnk
FROM by_product
QUALIFY rnk <= 3
```

Chọn theo câu hỏi business, không theo thói quen:

- `row_number`: đúng 3 dòng mỗi nước (3 slot trên dashboard, danh sách nhập hàng). Thêm khoá phụ (`stock_code`) để
  thứ tự xác định khi hoà.
- `rank`: "đừng bỏ sót ai ngang hạng"; có thể ra hơn 3 dòng. Trên Online Retail II 12/2010 - 11/2011, đổi
  `row_number` thành `rank` làm kết quả từ 114 lên 121 dòng.
- `dense_rank`: top 3 **mức** doanh thu.

Hai điểm ứng viên senior nói thêm: gom về grain sản phẩm **trước** khi xếp hạng, và lọc mã không phải hàng hoá. Không
lọc thì ở 18 trên 38 nước, "sản phẩm" số 1 là phí `POST`, `DOT` hoặc điều chỉnh `M`.

## Viết SQL tính doanh thu theo tháng kèm MoM và YoY. Có bẫy gì?

Ba bẫy:

1. **Tháng trống**: `GROUP BY month` không trả tháng không có giao dịch, nên `lag(revenue)` so với tháng cách hai
   tháng và `lag(revenue, 12)` không còn là cùng tháng năm trước. Sửa: sinh spine tháng bằng `generate_series`,
   `LEFT JOIN`, `coalesce(..., 0)`.
2. **Chia cho 0**: `revenue / NULLIF(lag(revenue) OVER (ORDER BY month), 0) - 1`. DuckDB trả `inf` khi chia cho 0,
   PostgreSQL báo lỗi; `NULL` mới đúng nghĩa "không xác định".
3. **Kỳ chưa đủ**: tháng cuối dở dang phải có cờ `is_complete` (ngày cuối tháng ≤ ngày cuối có dữ liệu) để dashboard
   vẽ nét đứt hoặc ẩn MoM.

Trên Online Retail II, MoM tháng 11/2011 là +30.7% nhưng YoY chỉ +2.7%: với doanh nghiệp quà tặng, MoM chủ yếu đo mùa
vụ. Báo cả hai, và dùng YoY khi hỏi về sức khoẻ kinh doanh.

## Case: ngày 10/12, CEO thấy dashboard "doanh thu tháng 12 giảm 58%". Bạn làm gì?

1. **Kiểm cách đo trước khi tìm nguyên nhân**: tháng 12 mới có dữ liệu tới 12:50 ngày 9, tức 8 ngày bán so với 26
   ngày của tháng 11. Con số -58% so 8 ngày với 26 ngày.
2. **So công bằng**: cùng 9 ngày đầu tháng 11: doanh thu +40.6%; cùng 9 ngày năm trước: +45.6%; số đơn +4.9% so với
   cùng ngày tháng trước. Luỹ kế năm tới 9/12 so với cùng kỳ: +3.8%.
3. **Kiểm con số so sánh có bị một giao dịch quyết định không**: trong 1-9/12/2011 có một hoá đơn 168 nghìn GBP bị huỷ
   12 phút sau. Doanh thu gộp vẫn tính nó; bỏ ra thì mức tăng so với năm trước còn khoảng 7.5% (module 08).
4. **Trả lời một câu**: "Doanh thu không giảm: đầu tháng 12 cao hơn cùng kỳ năm trước khoảng 7.5% sau khi bỏ một đơn
   lớn đã huỷ; con số -58% là do tháng 12 mới có 8 ngày".
5. **Sửa gốc**: dashboard thêm cờ kỳ chưa đủ, so cùng số ngày làm mặc định, cảnh báo đơn lớn bị huỷ.

## Mô tả cách viết cohort retention theo tháng bằng SQL. Những bẫy nào?

Ba CTE: `first_month` (`min(month)` theo khách trên **toàn bộ** lịch sử), `activity` (`SELECT DISTINCT customer_id,
cohort_month, date_diff('month', cohort_month, month) AS k`), rồi đếm khách theo `(cohort_month, k)` chia cỡ cohort.
Lưới `(cohort, k)` từ `generate_series` để ô không ai quay lại vẫn có dòng 0.

Bẫy:

- **Cắt trái**: dữ liệu Online Retail II bắt đầu 12/2009, nên cohort 12/2009 có 955 khách (gồm cả khách lâu năm),
  còn cohort 12/2010 chỉ 76. Cohort đầu có m1 35.3%, các cohort sau từ 9% tới 32%. Tách riêng hoặc bỏ cohort đầu.
- **Kỳ chưa đủ**: bỏ hoạt động tháng 12/2011, nếu không cột cuối mọi cohort tụt xuống.
- **NULL khác 0**: ô chưa quan sát được là NULL, ô quan sát được mà không ai quay lại là 0.
- **Thiếu DISTINCT**: đếm dòng hoá đơn thay vì khách, retention có thể vượt 100%.
- **Mùa vụ**: cohort 12/2009 có retention cao nhất ở k = 11 (11/2010, 49.5%): đó là mùa Giáng sinh, không phải "khách
  gắn bó dần".

## Funnel view → giỏ → mua bằng SQL: viết thế nào, đếm theo người hay theo phiên?

Funnel ngây thơ đếm `count(DISTINCT visitor_id)` theo từng loại sự kiện: bước sau có thể chứa người chưa qua bước
trước. Trên Retailrocket events, 3 321 visitor thêm giỏ mà không có lần xem nào trong dữ liệu. Funnel có thứ tự giữ mốc
thời gian từng bước:

```sql
WITH v AS (SELECT visitor_id, min(event_time) AS t_view FROM events WHERE event = 'view' GROUP BY 1),
c AS (SELECT v.visitor_id, min(e.event_time) AS t_cart
      FROM v JOIN events e ON e.visitor_id = v.visitor_id
       AND e.event = 'addtocart' AND e.event_time >= v.t_view
      GROUP BY 1)
-- p: transaction từ t_cart trở đi, tương tự
```

Theo visitor ra 1 404 179 → 32 934 → 9 952 (xem → mua 0.71%); theo phiên 30 phút ra 1 755 781 → 36 677 → 10 722
(0.61%). Theo visitor trả lời "bao nhiêu người cuối cùng mua"; theo phiên trả lời "một lượt ghé có dẫn tới mua
không", hợp để đo thay đổi giao diện. Trung vị từ lần xem đầu tới mua là 24 phút nhưng 10% mất hơn 9 ngày, nên funnel
theo phiên bỏ sót nhóm "mua sau".

## Một join làm tổng doanh thu tăng gấp năm. Vì sao, phát hiện và sửa thế nào?

Đó là **fan-out**: khoá join không duy nhất ở bảng bên kia, mỗi dòng bên trái khớp nhiều dòng bên phải. Trên dunnhumby,
`campaign_table` có 7 208 dòng cho 1 584 hộ (một hộ tới 17 campaign); join thẳng giao dịch với nó theo `household_key`
nhân 2.58 triệu dòng thành 13.9 triệu, doanh thu 8.06 triệu thành 43.8 triệu (5.44 lần).

Phát hiện **trước** khi join: `SELECT count(*), count(DISTINCT key) FROM bảng_phải`. Sau khi join: so số dòng và tổng
với trước join.

Sửa: gom bảng nhiều dòng về đúng grain trước (`SELECT DISTINCT household_key, DESCRIPTION`), hoặc gom bảng giao dịch
về grain hộ rồi mới join, hoặc dùng `EXISTS` khi chỉ cần "có/không". Không sửa bằng `SELECT DISTINCT` ở cuối (gộp mất
hai dòng mua thật giống nhau) và không tin `count(DISTINCT)`: nó làm cột đếm đúng trong khi cột `sum` vẫn bị nhân.

## NULL gây sai số ở những chỗ nào trong SQL phân tích?

| Chỗ | Hành vi | Cách đúng |
| --- | --- | --- |
| `count(*)` vs `count(col)` | `count(col)` bỏ NULL | Số khách là `count(DISTINCT customer_id)` |
| `avg(col)` | bỏ NULL khỏi cả tử và mẫu | Hỏi NULL là 0 hay "không biết" rồi mới `coalesce` |
| `col <> 'UK'` | dòng NULL bị loại | `col IS DISTINCT FROM 'UK'` |
| `x NOT IN (subquery có NULL)` | không trả dòng nào | `NOT EXISTS` |
| `LEFT JOIN b ... WHERE b.col = ...` | thành `INNER JOIN` | Đặt điều kiện vào `ON` |
| `INNER JOIN` bảng thuộc tính thiếu dòng | dòng bị rơi | `LEFT JOIN` + `coalesce(attr, 'Unknown')` |

Ví dụ dòng bị rơi: báo cáo doanh thu theo thu nhập trên dunnhumby dùng `INNER JOIN hh_demographic` chỉ còn 801/2 500
hộ, tức 55.8% doanh thu; mọi tỉ trọng trong báo cáo đó tính trên mẫu số sai.

## Case: hai báo cáo "doanh thu tháng 11" ra hai con số khác nhau. Bạn reconcile thế nào?

1. **Viết ra định nghĩa của từng báo cáo**: gộp hay ròng (có trừ đơn huỷ?), có tính phí vận chuyển (`POST`, `DOT`),
   có tính khách vãng lai, múi giờ và mốc ngày (`<= '2011-11-30'` trên TIMESTAMP mất cả ngày 30), nguồn bảng nào, chạy
   lúc nào (dữ liệu đến muộn).
2. **Thu hẹp**: so theo ngày, rồi theo nước, rồi theo hoá đơn; chỗ lệch thường tập trung ở vài ngày hoặc vài hoá đơn.
3. **Cầu đối chiếu** (bridge): báo cáo A → bỏ đơn huỷ → bỏ phí → đổi múi giờ → báo cáo B, mỗi bước một con số.
4. **Chốt một định nghĩa** với chủ metric (thường là tài chính), ghi vào tài liệu metric, đưa logic về một chỗ (view,
   model dbt), thêm test so tổng.

Kết quả mong muốn không phải "con số nào đúng" mà là "hai con số khác nhau vì X và Y, từ nay dùng định nghĩa Z".

## WHERE, HAVING và QUALIFY khác nhau thế nào?

Theo thứ tự thực thi logic: `WHERE` lọc **dòng** trước khi gom nhóm; `HAVING` lọc **nhóm** sau `GROUP BY` (dùng được
hàm tổng hợp); `QUALIFY` lọc sau khi tính **window function**. Ví dụ "nước có trên 50 khách, lấy 3 sản phẩm đầu mỗi
nước": `WHERE` bỏ dòng huỷ, `HAVING count(DISTINCT customer_id) > 50` ở bước gom theo nước, `QUALIFY row_number() OVER
(...) <= 3` ở bước xếp hạng. `QUALIFY` có ở DuckDB, Snowflake, BigQuery, Databricks; PostgreSQL thì bọc truy vấn con
và lọc ở ngoài.

## Running total và trung bình trượt: frame ROWS và RANGE khác nhau thế nào?

Có `ORDER BY` trong `OVER` mà không ghi frame thì mặc định là `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`:
các dòng **ngang giá trị** của khoá sắp xếp được coi là cùng vị trí và nhận cùng giá trị luỹ kế. Với Pareto (sắp theo
doanh thu), hai sản phẩm cùng 20 GBP sẽ cùng luỹ kế. `ROWS` tính theo **dòng vật lý**: đúng cho luỹ kế từng dòng và
trung bình trượt N dòng (`ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`).

Lưu ý thêm: trung bình trượt 7 **dòng** chỉ là 7 **ngày** khi bảng có đủ mọi ngày (spine). Cửa hàng Online Retail II
không giao dịch thứ Bảy, nên 7 dòng là khoảng 8 ngày lịch. Muốn theo thời gian thật thì dùng `RANGE BETWEEN INTERVAL 6
DAY PRECEDING AND CURRENT ROW` trên cột ngày.

## Case (product sense): marketing báo "hộ nhận campaign TypeC chi gấp 7 lần hộ không nhận, campaign rất hiệu quả". Bạn phản hồi thế nào?

Con số đúng (dunnhumby: 7 194 so với 1 029 doanh thu mỗi hộ cả kỳ), kết luận chưa đúng:

- **Selection bias**: campaign được gửi tới hộ chọn trước, thường là hộ mua nhiều. 1 584 hộ nhận campaign (63%) đã làm
  ra 88% doanh thu. So hai nhóm khác nhau từ đầu.
- **Thời gian**: doanh thu "cả kỳ" gồm cả trước khi nhận campaign.
- **Đo đúng**: so trước/sau trong cùng nhóm hộ, so với nhóm tương tự không nhận (matching), hoặc lần sau thiết kế nhóm
  đối chứng ngẫu nhiên (holdout). Metric chính: doanh thu tăng thêm trong thời gian campaign, trừ chi phí coupon.

Câu trả lời tốt: "Chưa đủ bằng chứng để nói campaign hiệu quả; đây là cách đo trong 2 tuần tới".

## Case: CEO hỏi "ngoài UK, thị trường nào nên đầu tư?". Bạn trả lời bằng SQL thế nào?

Không chỉ xếp theo doanh thu. Một truy vấn theo nước, hai kỳ 12 tháng đủ, gồm: doanh thu hai kỳ, tăng trưởng, **số
khách**, và **tỉ trọng của khách lớn nhất**. Trên Online Retail II (12/2010 - 11/2011 so với 12 tháng trước):

| Nước | Doanh thu | Tăng trưởng | Khách | Khách lớn nhất |
| --- | --- | --- | --- | --- |
| Netherlands | 273 718 | +1.9% | 9 | 98% |
| Germany | 220 883 | +12.3% | 93 | 8% |
| France | 202 438 | +43.7% | 86 | 9% |
| Australia | 138 521 | +349% | 9 | 90% |

Netherlands và Australia là **một khách sỉ** mỗi nước: quản lý như một tài khoản lớn, không phải thị trường. Germany
và France tăng trên nền khách rộng: đó là thị trường. Nói thêm giới hạn: doanh thu gộp, 16% doanh thu không có mã
khách, chưa có chi phí và lợi nhuận theo nước.

## Vì sao chọn DuckDB (chứ không phải Postgres hay pandas) cho phân tích trên file vài GB? Khi nào thì không?

DuckDB là database phân tích chạy **trong tiến trình**: không cần server, đọc thẳng CSV/Parquet/xlsx, lưu theo cột và
chạy song song, nên một truy vấn gom nhóm trên vài GB xong trong vài giây trên laptop. So với **Postgres**: không phải
dựng server, khai báo schema, nạp dữ liệu cho một việc một lần; Postgres lưu theo dòng nên quét bảng lớn chậm hơn.
So với **pandas**: SQL khai báo, tối ưu tự động, không phải nạp hết vào RAM; cú pháp gần chuẩn, mang sang warehouse dễ.
Trong module này, DuckDB đọc 1.04 triệu dòng xlsx trong khoảng 8 giây, pandas mất khoảng 50 giây.

Không chọn DuckDB khi: dữ liệu đã nằm trong warehouse (tổng hợp ở đó); nhiều người cần cùng một con số lặp lại (đưa vào
warehouse + BI); cần nhiều tiến trình ghi đồng thời hoặc phân quyền (Postgres, warehouse); hoặc là database phục vụ ứng
dụng.

## Truy vấn của bạn trên BigQuery/Snowflake chạy chậm và tốn tiền. Ở vai trò DA, bạn tối ưu gì trước?

1. **Chỉ đọc cột cần**: warehouse lưu theo cột, `SELECT *` đọc (và tính tiền) mọi cột.
2. **Lọc theo cột partition/cluster** (thường là ngày) bằng điều kiện trực tiếp (`event_date >= '2011-01-01'`), không
   bọc trong hàm (`date_trunc('month', event_date) = ...` có thể làm mất partition pruning).
3. **Gom sớm, join muộn**: tổng hợp bảng lớn về grain cần trước khi join bảng khác; tránh fan-out làm số dòng nổ.
4. **Không lặp lại công việc**: truy vấn chạy hằng ngày thì thành bảng tổng hợp (model incremental), dashboard đọc bảng
   nhỏ.
5. **Xem query plan / bytes scanned** trước khi chạy; dùng mẫu (`TABLESAMPLE`, một tháng) khi viết thử.

Phần index, cấu hình cluster là việc của Data Engineer; DA nên biết để mô tả vấn đề rõ khi nhờ.

## Lấy đơn hàng gần nhất của mỗi khách, và tính giá trị đơn trung vị bằng SQL.

Bản ghi mới nhất mỗi nhóm là mẫu `row_number`:

```sql
SELECT *
FROM orders
QUALIFY row_number() OVER (PARTITION BY customer_id ORDER BY order_time DESC, order_id DESC) = 1
```

Khoá phụ `order_id` để kết quả xác định khi hai đơn cùng thời điểm. Trung vị: `median(order_value)` (DuckDB) hoặc
`percentile_cont(0.5) WITHIN GROUP (ORDER BY order_value)` (PostgreSQL, Snowflake); BigQuery dùng
`APPROX_QUANTILES`. Trung vị quan trọng với DA vì giá trị đơn thường lệch phải: ở Online Retail II (12/2010 - 11/2011), giá trị hoá đơn
trung bình 523.90 GBP nhưng trung vị chỉ 303.95, vì đơn sỉ vài nghìn bảng kéo trung bình lên; "AOV tăng" có thể chỉ do
vài đơn lớn, nên báo cả hai.
