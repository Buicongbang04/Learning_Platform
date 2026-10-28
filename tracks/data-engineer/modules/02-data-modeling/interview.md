# Câu hỏi phỏng vấn: Data Modeling & Relational DB

## OLTP khác OLAP thế nào? Vì sao không chạy báo cáo thẳng trên database của ứng dụng?

OLTP phục vụ ứng dụng: nhiều giao dịch nhỏ đồng thời, đọc/ghi vài dòng theo khoá, cần độ trễ thấp
và tính đúng; schema chuẩn hoá (3NF), lưu theo dòng. OLAP phục vụ phân tích: ít truy vấn nhưng mỗi
truy vấn quét và tổng hợp hàng triệu dòng trên vài cột; schema dimensional (star), lưu theo cột.

Chạy báo cáo nặng trên OLTP sẽ tranh I/O, CPU, buffer cache với request của khách; transaction đọc
dài giữ snapshot cũ làm bloat (PostgreSQL); và schema 3NF buộc analyst join 6–7 bảng, dễ sai.
Giải pháp thường dùng: read replica cho truy vấn nhẹ, còn phân tích thì chép sang warehouse
(batch/CDC) và mô hình lại thành star schema.

## Giải thích 1NF, 2NF, 3NF bằng một ví dụ.

Lấy bảng phẳng Olist `(order_id, order_item_id, customer_id, customer_city, product_id, product_category, price, payment_types)`.

- **1NF**: mỗi ô nguyên tử. `payment_types = 'credit_card, voucher'` vi phạm → tách `order_payments`.
- **2NF**: không phụ thuộc một phần khoá ghép. Khoá là `(order_id, order_item_id)` nhưng
  `customer_id` chỉ phụ thuộc `order_id` → tách `orders(order_id, customer_id)`.
- **3NF**: không phụ thuộc bắc cầu. `order_id → customer_id → customer_city` → tách
  `customers(customer_id, customer_city)`; tương tự `product_id → product_category` → `products`.

Kết quả: `customers`, `orders`, `order_items`, `products`, `order_payments`. Mục đích là tránh
update/insert/delete anomaly: thành phố khách chỉ lưu một chỗ.

## BCNF khác 3NF ở điểm nào? Thực tế có cần đạt BCNF không?

3NF cho phép một dependency `X → A` nếu A là cột thuộc một candidate key (prime attribute). BCNF
chặt hơn: mọi `X → A` không tầm thường thì X phải là superkey. Khác biệt chỉ xuất hiện khi có
nhiều candidate key ghép chồng nhau, ví dụ `(seller_id, zip, carrier)` với `carrier → zip`.

Thực tế hầu hết schema 3NF đã là BCNF. Khi không, tách về BCNF có thể làm mất khả năng ép một
dependency bằng constraint trong một bảng (không "dependency preserving"), nên nhiều đội chấp nhận
3NF và ép phần còn lại bằng logic hoặc trigger. Câu trả lời tốt: biết định nghĩa, biết ví dụ, và
biết đây là đánh đổi chứ không phải luật.

## Khi nào bạn chủ động denormalize?

Khi workload đọc áp đảo và join là nút cổ chai; khi cần lưu giá trị tại thời điểm (giá lúc mua
trong `order_items.price`, địa chỉ giao hàng trên đơn); ở tầng phân tích (star schema, One Big
Table); cache tổng hợp (`orders.total_value`) để tránh tính lại. Điều kiện: có một nguồn sự thật
chuẩn hoá, bản denormalize được sinh ra/cập nhật bằng pipeline hoặc trigger, và có kiểm tra đối
soát. Đánh đổi là dung lượng và rủi ro dữ liệu lệch nhau.

## Fact table và dimension table là gì? Grain là gì và vì sao quan trọng?

Fact chứa số đo của sự kiện nghiệp vụ (price, freight, quantity) cùng foreign key tới dimension;
nhiều dòng, ít cột. Dimension chứa ngữ cảnh mô tả (khách, sản phẩm, ngày) để lọc và nhóm; ít dòng
hơn, nhiều cột.

Grain là định nghĩa "một dòng fact đại diện cho cái gì", ví dụ "một item trong một đơn hàng". Grain
phải chốt trước khi chọn dimension và measure, vì mọi measure phải đúng grain. Đặt `payment_value`
(grain đơn hàng) vào fact grain item thì `SUM` sẽ nhân đôi với đơn có hai item — lỗi double
counting kinh điển. Grain càng chi tiết (atomic) càng linh hoạt; tổng hợp thì làm sau.

## Star schema và snowflake schema khác nhau thế nào? Bạn chọn cái nào?

Star: fact ở giữa, mỗi dimension là một bảng phẳng denormalized, truy vấn chỉ cần join một bước.
Snowflake: dimension được chuẩn hoá thành nhiều bảng (product → category → department), tiết kiệm
dung lượng, sửa thuộc tính cha một chỗ, nhưng nhiều join hơn và khó hiểu với người dùng BI.

Trên warehouse cột hiện đại, dung lượng lặp lại được nén gần như miễn phí, nên tôi chọn **star làm
mặc định**. Snowflake chỉ hợp lý khi một hierarchy rất lớn được dùng chung nhiều dimension, hoặc
dimension cực lớn và thay đổi thường xuyên ở cấp cha.

## Surrogate key là gì? Vì sao không dùng luôn natural key trong warehouse?

Surrogate key là khoá nguyên vô nghĩa do warehouse sinh. Lý do dùng: (1) SCD type 2 cần nhiều dòng
cho cùng một natural key; (2) tích hợp nhiều nguồn có thể trùng hoặc đổi định dạng khoá; (3) cách
ly warehouse khỏi việc nguồn tái sử dụng hay đổi khoá; (4) khoá nguyên nhỏ, join nhanh; (5) có dòng
"Unknown/-1" cho fact đến trước dimension (late-arriving dimension) thay vì NULL. Natural key vẫn
được giữ trong dimension làm cột thuộc tính để tra cứu. Trong dbt, nhiều đội dùng hash của natural
key (+ valid_from) làm surrogate key để tính được một cách tất định, không cần sequence.

## Giải thích các loại SCD. Viết SCD type 2 thế nào?

Type 0 giữ nguyên; type 1 ghi đè (mất lịch sử); type 2 thêm dòng mới với `valid_from`, `valid_to`,
`is_current` (giữ đủ lịch sử); type 3 thêm cột `previous_value` (một bước lịch sử); type 4 tách bảng
history; type 6 kết hợp 1+2+3.

SCD2 trong một transaction:

```sql
UPDATE dim_customer d SET valid_to = :as_of, is_current = FALSE
FROM stg s
WHERE d.customer_id = s.customer_id AND d.is_current
  AND (d.city IS DISTINCT FROM s.city OR d.state IS DISTINCT FROM s.state);

INSERT INTO dim_customer (customer_id, city, state, valid_from, valid_to, is_current)
SELECT s.customer_id, s.city, s.state, :as_of, DATE '9999-12-31', TRUE
FROM stg s LEFT JOIN dim_customer d ON d.customer_id = s.customer_id AND d.is_current
WHERE d.customer_id IS NULL;
```

Điểm cần nói: so sánh NULL-safe hoặc so sánh hash, idempotent khi chạy lại cùng snapshot, khoảng
nửa mở `[valid_from, valid_to)`, xử lý dòng bị xoá ở nguồn, và fact tra surrogate key theo thời
điểm sự kiện.

## Fact đến trước dimension (late-arriving dimension) thì xử lý thế nào?

Ví dụ đơn hàng tới nhưng khách chưa có trong `dim_customer` (CDC của bảng customers chậm). Các cách:
(1) gán `customer_key = -1` (Unknown) rồi chạy job sửa lại sau — đơn giản nhưng phải nhớ re-key;
(2) tạo **inferred member**: chèn một dòng dimension tạm chỉ có natural key, các thuộc tính để
"pending", khi bản ghi thật tới thì cập nhật dòng đó theo type 1 (không tạo phiên bản mới);
(3) giữ fact trong staging chờ tới khi đủ dimension — chậm và phức tạp. Phương án 2 là phổ biến nhất.

## B-tree index hoạt động thế nào? Khi nào index không được dùng?

B-tree là cây cân bằng, lá chứa khoá đã sắp xếp và con trỏ tới dòng, các lá nối nhau. Tìm theo `=`
hoặc khoảng tốn O(log n) rồi quét lá liên tiếp; còn hỗ trợ `ORDER BY` không cần sort.

Index không được dùng khi: truy vấn trả về phần lớn bảng (seq scan rẻ hơn random I/O); bọc cột
bằng hàm hoặc ép kiểu (`WHERE date(ts) = ...`, `WHERE id::text = ...`); `LIKE '%abc'`; điều kiện
không chứa cột đầu của composite index; thống kê cũ khiến planner ước lượng sai; bảng quá nhỏ;
hoặc so sánh khác collation/kiểu. Cách kiểm: `EXPLAIN (ANALYZE, BUFFERS)`.

## Composite index `(a, b)` và hai index riêng `(a)`, `(b)` khác nhau thế nào? Covering index là gì?

Composite `(a, b)` sắp theo a rồi b, nên phục vụ `WHERE a = ?`, `WHERE a = ? AND b > ?`,
`WHERE a = ? ORDER BY b` rất tốt nhưng không phục vụ `WHERE b = ?` (leftmost prefix). Hai index
riêng có thể được kết hợp bằng bitmap AND, nhưng chậm hơn và không cho thứ tự sắp xếp. Quy tắc:
cột lọc bằng trước, cột khoảng/sort sau.

Covering index chứa mọi cột truy vấn cần (PostgreSQL: `INCLUDE (price)`), nên engine trả kết quả
từ index mà không quay về bảng: **Index Only Scan** (PG) hay `USING COVERING INDEX` (SQLite). Đánh
đổi: index to hơn, ghi chậm hơn; ở PG còn phụ thuộc visibility map (cần VACUUM).

## Giải thích ACID và các isolation level. PostgreSQL mặc định dùng level nào?

Atomicity (tất cả hoặc không), Consistency (constraint luôn đúng), Isolation (giao dịch đồng thời
không thấy nhau dở dang), Durability (commit rồi thì không mất, nhờ WAL).

Isolation level theo chuẩn: Read Uncommitted (có dirty read), Read Committed (không dirty read,
vẫn có non-repeatable read và phantom), Repeatable Read (không non-repeatable), Serializable (như
chạy tuần tự). PostgreSQL mặc định **Read Committed**; Repeatable Read của PG là snapshot isolation
nên cũng không có phantom nhưng vẫn có write skew; Serializable dùng SSI và có thể abort transaction
với lỗi `40001`, ứng dụng phải retry. PG dùng MVCC nên reader không chặn writer.

## Hai request cùng mua sản phẩm cuối cùng trong kho. Làm sao không bán quá?

Đây là lost update / race condition. Cách đơn giản và mạnh nhất là atomic conditional update:

```sql
UPDATE stock SET qty = qty - 1 WHERE product_id = $1 AND qty >= 1;
```

Nếu rowcount = 0 thì hết hàng, rollback cả đơn. Ngoài ra có `CHECK (qty >= 0)` làm lưới an toàn.
Phương án khác: `SELECT ... FOR UPDATE` (pessimistic, khoá dòng; khoá nhiều sản phẩm thì sắp xếp
theo id để tránh deadlock), optimistic locking bằng cột `version` và retry, hoặc chạy Serializable
kèm retry. Tôi tránh mẫu "đọc vào ứng dụng, tính, rồi ghi đè" vì nó chính là nguồn lỗi.

## Làm sao để một job nạp dữ liệu hằng ngày vào PostgreSQL idempotent và an toàn khi lỗi giữa chừng?

Bọc phần ghi trong một transaction và thiết kế theo "thay thế phần dữ liệu của lần chạy":

```sql
BEGIN;
DELETE FROM fact_order_items WHERE purchase_date = '2018-03-01';
INSERT INTO fact_order_items SELECT ... FROM stg WHERE purchase_date = '2018-03-01';
COMMIT;
```

Hoặc upsert `INSERT ... ON CONFLICT (order_id, order_item_id) DO UPDATE` / `MERGE`. Với bảng lớn,
nạp vào partition hoặc bảng tạm rồi `ATTACH PARTITION`/đổi tên trong transaction. Chạy lại cùng
ngày cho cùng kết quả; lỗi giữa chừng thì rollback, người đọc không thấy dữ liệu nửa vời. Bulk load
bằng `COPY` vào staging, unique constraint để chặn trùng.

## Thiết kế mô hình dữ liệu phân tích cho quy trình giao hàng của Olist.

Câu hỏi nghiệp vụ: tỷ lệ giao trễ theo bang/seller/tháng, thời gian từng chặng (duyệt, giao cho
vận chuyển, tới khách), ảnh hưởng của trễ tới review score.

Đề xuất:

- `fact_order_delivery` — **accumulating snapshot**, grain một dòng/đơn hàng; các mốc
  `purchase_date_key`, `approved_date_key`, `carrier_date_key`, `delivered_date_key`,
  `estimated_date_key` (role-playing `dim_date`); measure: `approval_hours`, `shipping_days`,
  `delivery_days`, `delay_days`, `is_late`, `freight_value`, `items_count`, `review_score`. Dòng được
  cập nhật khi đơn qua mốc mới.
- `fact_order_items` — transaction fact grain item cho doanh thu theo seller/sản phẩm.
- Dimension: `dim_customer` (SCD2 theo city/state, vì phân tích theo vị trí tại thời điểm mua),
  `dim_seller` (SCD2 hoặc 1), `dim_product`, `dim_date`, `dim_geolocation` (theo zip prefix),
  `dim_order_status` hoặc junk dimension.
- Đơn có nhiều seller: hoặc giữ grain đơn và gắn `seller_key` = seller chính, hoặc tách grain
  (order, seller) — phải nêu rõ và thống nhất với người dùng.

Bàn thêm: nạp incremental theo `order_purchase_timestamp`/updated_at, xử lý đơn huỷ, partition fact
theo tháng, kiểm tra chất lượng (delivered_date ≥ purchase_date), và cách tính trễ (so ngày hay giờ).

## Một truy vấn dashboard trên PostgreSQL đang chạy 30 giây. Bạn điều tra và tối ưu thế nào?

1. Lấy truy vấn thật và tần suất từ `pg_stat_statements`; xác nhận đó là nút cổ chai.
2. `EXPLAIN (ANALYZE, BUFFERS)`: tìm node tốn nhất, seq scan trên bảng lớn, ước lượng `rows` lệch
   nhiều so với thực tế (→ `ANALYZE`, tăng statistics target), sort/hash tràn đĩa (`work_mem`),
   nested loop với vòng ngoài lớn.
3. Sửa theo nguyên nhân: composite/covering index đúng thứ tự cột; viết lại điều kiện sargable
   (bỏ hàm bọc cột, dùng khoảng thời gian thay `date(ts) =`); partition theo thời gian để pruning;
   bỏ `SELECT *`; tiền tổng hợp bằng materialized view hoặc bảng summary làm mới định kỳ.
4. Đo lại, kiểm tra tác động lên ghi (thêm index làm chậm INSERT).
5. Nếu bản chất là phân tích quét lớn, câu trả lời dài hạn là đưa sang warehouse/columnar
   (DuckDB, BigQuery, ClickHouse) thay vì cố ép OLTP.
