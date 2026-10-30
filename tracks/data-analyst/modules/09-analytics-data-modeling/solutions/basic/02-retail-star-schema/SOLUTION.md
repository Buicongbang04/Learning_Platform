# Lời giải: star schema cho Online Retail II

## Cách làm

1. **`dim_product`**: đếm số dòng hợp lệ theo `(stock_code, description)`, xếp hạng trong từng mã bằng
   `row_number() OVER (PARTITION BY stock_code ORDER BY n DESC, description)`, giữ hạng 1. Quy tắc hoà phải
   **tất định** (cùng dữ liệu luôn ra cùng mô tả), nếu không dashboard đổi tên sản phẩm giữa hai lần build.
   `product_key` đánh số theo `stock_code`; `is_merchandise` bằng `regexp_matches(stock_code, '^[0-9]{5}')`
   (mã như `85123A` vẫn là hàng hoá).
2. **`dim_customer`**: một dòng hằng cho unknown member `UNION ALL` truy vấn `GROUP BY customer_id` với
   `arg_max(country, invoiced_at)` (quốc gia ở lần mua hợp lệ muộn nhất) và `min(invoiced_at)`.
3. **`fct_sales_line`**: từ `valid_lines`, `JOIN dim_product` (mọi mã hợp lệ đều có trong dimension vì
   dimension dựng từ cùng view), `LEFT JOIN dim_customer` rồi `coalesce(customer_key, 0)`, `date_key` bằng
   `strftime(invoiced_at, '%Y%m%d')`.

Lời giải đầy đủ ở `star_schema.sql` cùng thư mục.

## Vì sao như vậy

- **Grain là dòng nguồn, không phải (hoá đơn, mã hàng)**: 9 566 cặp lặp lại và 5 226 dòng trùng y hệt dòng khác.
  Dedupe "cho sạch" là quyết định nghiệp vụ, không phải việc của bước dựng star; khi chưa có xác nhận, giữ mọi
  dòng và để `line_key = source_row` làm khoá.
- **Dimension một dòng mỗi khoá là điều kiện của mọi join đúng**: dựng bằng `DISTINCT StockCode, Description`
  cho 4 161 dòng và làm doanh thu theo sản phẩm phình 12.3%. Mô tả "nhiều dòng nhất" là cách chọn tên chuẩn
  hợp lý khi các biến thể chủ yếu là lỗi chính tả (`23196` có cả "RETO LEAVES..."); nếu nghiệp vụ muốn tên
  **mới nhất**, đổi `ORDER BY n DESC` thành thời điểm dòng cuối, và ghi quyết định đó vào mô tả model.
- **Unknown member** giữ 132 220 dòng (1 428 hoá đơn, 16.5% doanh thu) trong mọi join. Dashboard thấy một dòng
  "Unknown" thay vì mất tiền không dấu vết.
- **Giá ở fact**: 3 366 / 3 922 mã có nhiều mức giá trong năm. **Quốc gia ở fact**: quốc gia đi theo hoá đơn và
  khách vãng lai cũng có; 8 khách có hai quốc gia, nên `current_country` chỉ dùng cho CRM.
- **Mã phí giữ trong fact, gắn cờ ở dimension**: 22 mã, 395 667.93 GBP (3.7%). Finance cần chúng trong tổng
  doanh thu; báo cáo sản phẩm lọc `is_merchandise`.

## Con số tham chiếu (bộ thật, sheet `Year 2010-2011`)

| Đại lượng | Giá trị |
| --- | --- |
| `fct_sales_line` | 530 105 dòng, 10 666 702.54 GBP |
| Khách vãng lai (`customer_key = 0`) | 132 220 dòng, 1 428 hoá đơn, 1 755 276.64 GBP |
| `dim_product` | 3 922 mã; 22 mã không phải hàng hoá, 395 667.93 GBP |
| `dim_customer` | 4 339 dòng (4 338 khách + unknown member); 3 920 có `current_country` United Kingdom |
| `dim_date` | 374 ngày (01/12/2010–09/12/2011), trong đó 305 ngày có đơn |
| Top hàng hoá theo doanh thu gộp | `22423` REGENCY CAKESTAND 3 TIER 174 484.74; `23843` PAPER CRAFT, LITTLE BIRDIE 168 469.60 (1 dòng); `85123A` 104 518.80 |

## Đáp án trắc nghiệm

- `guest-lines` (b) **132 220**. 1 428 (a) là số **hoá đơn** của khách vãng lai, 4 339 (c) là số dòng
  `dim_customer`.
- `non-merch-share` (c) **khoảng 3.7%**. 16.5% (b) là phần của khách vãng lai; 12.3% (d) là mức phình do fan-out.
- `second-product` (a): một dòng 168 470 GBP là hoá đơn 581483 (80 995 cái), bị huỷ bằng C581484 sau 12 phút
  (module 08, Advanced 01). Doanh thu gộp vẫn đúng định nghĩa, nhưng báo cáo top sản phẩm không ghi chú sẽ làm
  một đơn bị huỷ thành "sản phẩm bán chạy thứ 2". Xoá khỏi fact (b) làm lệch số với Finance; đổi grain (c) không
  giải quyết gì; đây là hàng hoá thật, không phải mã phí (d).
- `dim-customer-rows` (d): dòng unknown member. Khách có hai quốc gia (a) vẫn một dòng vì `current_country` là
  type 1; khách chỉ có đơn huỷ (b) không vào dimension vì dimension dựng từ dòng hợp lệ.
- `country-in-fact` (a): quốc gia là thuộc tính của từng hoá đơn. (b), (c), (d) sai về kỹ thuật: DuckDB join cột
  chữ bình thường và dimension chủ yếu là cột chữ.
- `price-in-fact` (b): 3 366 / 3 922 mã có nhiều giá. Giá là measure **non-additive** (c sai), và dimension hoàn
  toàn có thể chứa số như giá niêm yết (a sai).
