# Hướng làm: star schema từ schema Grocery Sales

Bài Advanced không có một đáp án duy nhất. Dưới đây là hướng làm, các quyết định cần cân nhắc, con số đối soát cấu
trúc trên bộ thật và rubric chấm. Bộ này là dữ liệu sinh giả: mọi con số dưới đây là **số dòng và số khoá**, không
phải chỉ số kinh doanh.

## Hướng làm

1. **Kiểm grain trước khi chọn.** `count(DISTINCT TransactionNumber)` = `count(*)` = 6 758 125: mỗi "giao dịch" chỉ
   có một dòng, nên grain giỏ hàng trùng grain dòng và mọi chỉ số giỏ (số món mỗi giỏ, giá trị giỏ) đều tầm thường.
   Grain của `fct_sales`: một dòng = một `SalesID`. `TransactionNumber` giữ lại làm degenerate dimension.
2. **Làm phẳng dimension.** `categories` vào `dim_product`; `cities` + `countries` vào `dim_customer` và
   `dim_employee`. Snowflake đúng chuẩn hoá nhưng bắt mỗi dashboard tự join ba bước; dimension chỉ vài trăm tới
   vài chục nghìn dòng nên lặp tên thành phố không đáng kể.
3. **Unknown member ở mọi dimension**, khoá `-1`, rồi `LEFT JOIN` + `coalesce(key, -1)` trong fact. `SalesDate` rỗng
   cũng về `date_key = -1`: không xoá dòng, để tổng số dòng fact luôn khớp nguồn.
4. **Cột tiền.** `TotalPrice` luôn bằng 0 nên không dùng. `net_amount = Quantity * Price * (1 - Discount)` với
   `Price` là giá **hiện tại** của sản phẩm (`ModifyDate` từ 01/2017 tới 05/2018, không có bảng lịch sử giá). Ghi rõ
   đây là ước lượng theo giá hiện tại; nếu có lịch sử giá thì lấy giá có hiệu lực tại `SalesDate` (giống SCD type 2).
   Sản phẩm không có giá thì để NULL, không thay bằng 0 (0 làm tổng thấp đi mà không ai biết).

Đoạn SQL tham chiếu cho fact (dimension tương tự, xem gợi ý trong đề):

```sql
CREATE OR REPLACE TABLE fct_sales AS
SELECT s.SalesID AS sales_id, s.TransactionNumber AS transaction_number,
       coalesce(CAST(strftime(s.SalesDate, '%Y%m%d') AS INTEGER), -1) AS date_key,
       coalesce(c.customer_key, -1) AS customer_key, coalesce(p.product_key, -1) AS product_key,
       coalesce(e.employee_key, -1) AS salesperson_key,
       s.Quantity AS quantity, p.list_price AS unit_price, s.Discount AS discount,
       s.Quantity * p.list_price * (1 - s.Discount) AS net_amount
FROM raw_sales s
LEFT JOIN dim_product p ON p.product_id = s.ProductID
LEFT JOIN dim_customer c ON c.customer_id = s.CustomerID
LEFT JOIN dim_employee e ON e.employee_id = s.SalesPersonID;
```

## Con số đối soát cấu trúc (bộ thật)

| Đại lượng | Giá trị |
| --- | --- |
| `sales` | 6 758 125 dòng, 6 758 125 `TransactionNumber` khác nhau, `TotalPrice` = 0 ở mọi dòng |
| `SalesDate` rỗng | 67 526 dòng (khoảng 1%) → `date_key = -1`; ngày có giá trị từ 01/01/2018 tới 09/05/2018 |
| Khoá ngoại không khớp | 0 dòng cho khách, sản phẩm và nhân viên |
| Dimension | 452 sản phẩm (11 danh mục), 98 759 khách, 23 nhân viên, 96 thành phố đều thuộc một quốc gia; bảng `countries` có 206 dòng |
| Giá trị `Unknown` trong nguồn | `IsAllergic` 130 sản phẩm, `Resistant` 140 sản phẩm |
| `Discount` | chỉ ba giá trị: 0, 0.1, 0.2 |

Đọc như một DA: 206 quốc gia mà chỉ một quốc gia có thành phố, mọi dòng có khoá khớp hoàn hảo, giỏ hàng một món:
một database thật hiếm khi sạch và kỳ lạ cùng lúc như vậy. Đó là thêm một dấu hiệu dữ liệu sinh giả, không phải
lý do để tin nó.

## Các quyết định cần cân nhắc

- **Star hay snowflake**: star cho người dùng BI; snowflake chỉ đáng khi dimension rất lớn hoặc nhiều fact dùng chung
  một bảng con (ví dụ `dim_geography` dùng chung cho khách và nhân viên, có thể là outrigger).
- **Khoá thay thế**: dùng khoá tự nhiên được vì không có lịch sử; khi cần SCD2 (khách đổi thành phố) thì sinh khoá
  mới cho mỗi phiên bản, fact trỏ theo ngày bán.
- **Role-playing**: `employees` chỉ đóng một vai (người bán). Nếu sau này có "người duyệt giảm giá" thì cùng
  `dim_employee` đóng hai vai, fact có hai khoá.
- **Thông tin cá nhân**: `Address`, `BirthDate` không cần cho báo cáo bán hàng; để ngoài dimension hoặc hạn chế
  quyền. Đây là quyết định mà DA nên chủ động nêu.
- **Test**: unique/not_null khoá và relationships (error); số dòng fact = số dòng nguồn (error); tỉ lệ `date_key =
  -1` vượt ngưỡng (warn); `TotalPrice` khác 0 (warn: nguồn đổi thì xem lại công thức tiền).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Grain | 15 | Câu "một dòng = ..." rõ; đã kiểm grain giỏ hàng bằng truy vấn và giải thích vì sao bỏ |
| Bảng, khoá, sơ đồ | 15 | Sơ đồ fact + 4 dimension; lý do làm phẳng; lý do dùng khoá tự nhiên hoặc khoá sinh |
| SQL | 20 | Test pass; unknown member ở mọi dimension; không mất dòng; chạy lại được |
| Cột tiền | 15 | Không dùng `TotalPrice`; nêu rõ giá hiện tại vs giá lúc bán và hệ quả; NULL thay vì 0 khi thiếu giá |
| Data test | 10 | Khoá, relationships, đối soát số dòng; phân biệt error/warn có lý do; ghi kết quả đối soát trên bộ thật |
| Quyết định khác | 10 | Ít nhất hai trong: `SalesDate` rỗng, giá trị `Unknown`, SCD cho thành phố, thông tin cá nhân, role-playing |
| Không rút insight | 15 | Nói rõ bộ là sinh giả (dẫn module 06), không có con số kinh doanh nào trong tài liệu, có câu trả lời mẫu cho stakeholder hỏi "bán chạy nhất" |

Từ 70 điểm: team BI dựng được dashboard trên mô hình này khi có database thật cùng schema.

## Sai lầm hay gặp

- Inner join fact với dimension: mất 67 526 dòng thiếu ngày mà không ai biết.
- Dùng `TotalPrice` (luôn 0) hoặc thay giá thiếu bằng 0.
- Giữ snowflake rồi để người dùng BI tự join `customers → cities → countries`.
- Viết "danh mục X bán chạy nhất" trong tài liệu thiết kế: bộ sinh giả không trả lời được câu đó.
