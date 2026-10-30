# Lời giải: dashboard doanh số cho Head of Sales trên Metabase

## Cách làm

1. **`KPI_SQL`**: CTE `monthly` (tháng, tổng doanh thu) có `WHERE {{country}}`; `FROM bounds b LEFT JOIN monthly
   cur ON cur.month = b.last_month LEFT JOIN monthly prev ON prev.month = CAST(b.last_month - INTERVAL '1 month' AS
   DATE)`; `revenue = COALESCE(cur.revenue, 0)`, `mom_pct = COALESCE(cur.revenue, 0) / NULLIF(prev.revenue, 0) - 1`,
   làm tròn 2 và 4 số.
2. **`TREND_SQL`**: `FROM da.online_retail_ii, bounds WHERE {{country}} AND CAST(date_trunc('month', invoicedate)
   AS DATE) <= bounds.last_month`, nhóm theo tháng, sắp tăng.
3. **`TOP_PRODUCTS_SQL`**: `invoicedate >= last_month AND invoicedate < last_month + INTERVAL '1 month'` (khoảng nửa
   mở, giữ được phút cuối tháng), `LEFT(stockcode, 1) BETWEEN '0' AND '9'`, `MIN(description)`, `ORDER BY revenue
   DESC, stockcode LIMIT 10`.
4. **`MONTHLY_TABLE_SQL`**: `COUNT(DISTINCT invoice)`, `COUNT(DISTINCT customer_id)`, `SUM(revenue) /
   COUNT(DISTINCT invoice)`, `ORDER BY 1 DESC`.
5. **`LAYOUT`**: `kpi (0, 0, 6, 8)`, `trend (0, 6, 18, 8)`, `top_products (8, 0, 12, 9)`, `monthly_table (8, 12, 12,
   9)`.
6. **`card_payload`**: tag `country` kiểu `dimension`, `dimension: ["field", country_field_id, None]`,
   `widget-type: "string/="`, `display-name: "Quốc gia"`.
7. **`dashcards`**: `id` âm theo thứ tự, vị trí từ `LAYOUT`, `parameter_mappings` một phần tử cho mỗi card.
8. **`validate_layout`**: kiểm kích thước, biên lưới, rồi so từng cặp bằng điều kiện giao của hai hình chữ nhật
   (so sánh chặt `<`).
9. **`upsert_dashboard`**: tìm theo tên (chưa archive), tạo nếu chưa có, `validate_layout` trước khi gửi, `PUT
   {"parameters": [PARAMETER], "dashcards": [...]}`. `PUT` với danh sách dashcard là **thay toàn bộ** dashcard của
   dashboard, nên chạy lại không nhân đôi.

## Vì sao như vậy

- **Tháng đủ gần nhất, mốc từ dữ liệu**: dữ liệu dừng 09/12/2011. KPI "tháng hiện tại" sẽ báo 638 810.68 GBP, giảm
  58% so với tháng 11, trong khi thực ra tháng 12 mới có 9 ngày. Mốc tính từ `max(invoicedate)` (không gõ cứng
  "2011-11") nên dashboard vẫn đúng khi dữ liệu nạp thêm.
- **Mốc tính trên toàn bộ dữ liệu, doanh thu tính trên nước đang lọc**: CTE `bounds` không có `{{country}}`. Nếu
  đặt mốc trong phần đã lọc, một nước nhỏ ngừng mua từ tháng 9 sẽ có "tháng đủ gần nhất" là tháng 8, và tile KPI
  của các nước nói về các tháng khác nhau.
- **`LEFT JOIN` từ `bounds`**: nước không bán gì trong tháng vẫn ra một dòng doanh thu 0, card không bị trống (card
  trống trên dashboard bị đọc là "lỗi", không phải "0").
- **Field filter, không alias**: Metabase sinh `"da"."online_retail_ii"."country" = 'Germany'`; nếu `FROM` đặt alias,
  tên bảng đầy đủ không còn trong câu và query lỗi. Khi bộ lọc trống, điều kiện là `1 = 1`.
- **Bộ lọc nối vào mọi card**: một card không có `parameter_mappings` vẫn hiện số toàn công ty khi người xem chọn
  Germany, lỗi đọc số kinh điển. Test kiểm mọi dashcard đều có mapping.
- **Top sản phẩm chỉ gồm sản phẩm**: không lọc thì `DOT` (DOTCOM POSTAGE, 36 905.40 GBP) đứng đầu tháng 11/2011.
  Quy tắc "ký tự đầu là chữ số" bỏ 4 709 trên 1 019 654 dòng: phí ship (`POST`, `DOT`, `C2`), điều chỉnh (`M`,
  `ADJUST`, `BANK CHARGES`), voucher, nhưng cũng bỏ 124 dòng hàng thật mã `DCGS...` (16 mã); đánh đổi chấp nhận được
  cho top 10, cần ghi trong mô tả card. Bản production nên có cột `is_product` ở bảng dimension sản phẩm.
- **Bố cục F**: KPI góc trái trên (mắt nhìn đầu tiên), trend bên phải cùng hàng (bối cảnh của KPI), breakdown và
  bảng chi tiết hàng dưới (trả lời "vì sao"). `validate_layout` chạy trước khi `PUT` để lỗi bố cục bị bắt trong
  code review, không phải khi Head of Sales mở dashboard.

## Con số tham chiếu (Metabase thật)

| Card | Không lọc | Germany |
| --- | --- | --- |
| KPI tháng đủ gần nhất | 11/2011: 1 509 496.33 GBP, MoM +30.69% (10/2011: 1 154 979.30) | 28 025.02 GBP, MoM -11.42% (10/2011: 31 638.42) |
| Trend | 24 tháng, 12/2009 tới 11/2011 | |
| Top sản phẩm 11/2011 | `23084` RABBIT NIGHT LIGHT 34 556.72; `22086` PAPER CHAIN KIT 50'S CHRISTMAS 28 985.04; `22197` POPCORN HOLDER 14 195.60 | `22423` REGENCY CAKESTAND 3 TIER 1 215.30 |
| Bảng chi tiết 11/2011 | 2 769 hoá đơn, 1 664 khách, AOV 545.14 | |

Đọc cho Head of Sales: tháng 11 tăng 31% so với tháng 10 nhờ mùa Giáng sinh (top sản phẩm là đèn ngủ và đồ
trang trí), nhưng Germany đi ngược, giảm 11%. Đó là câu hỏi cho phân tích ad-hoc tiếp theo, không phải thêm card.

## Sai lầm hay gặp

- KPI dùng `date_trunc('month', now())` hoặc tháng cuối có dữ liệu: báo "giảm 58%".
- Đặt `{{country}}` trong CTE tính mốc tháng.
- `FROM da.online_retail_ii r`: field filter lỗi.
- `invoicedate <= '2011-11-30'`: mất mọi giao dịch trong ngày 30/11 sau 00:00.
- Quên `parameter_mappings` ở một card; hoặc `validate_layout` coi hai card chạm cạnh là chồng.
