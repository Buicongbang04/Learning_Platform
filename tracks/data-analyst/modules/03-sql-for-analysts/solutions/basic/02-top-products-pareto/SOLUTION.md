# Lời giải: top 3 mỗi quốc gia và Pareto/ABC

## Cách làm

### `top3_per_country.sql`

1. **`sales`**: lọc dòng hợp lệ, kỳ nửa mở `>= '2010-12-01' AND < '2011-12-01'` (không cần nghĩ tới giờ phút
   của ngày cuối) và chỉ hàng hoá `regexp_matches(stock_code, '^[0-9]{5}')`.
2. **`by_product`**: tổng theo `country, stock_code`. Grain của bảng kết quả là "một nước × một mặt hàng",
   phải gom về đúng grain này **trước** khi xếp hạng; xếp hạng trên dòng giao dịch sẽ cho "top 3 dòng".
3. **`ranked`**: `row_number() OVER (PARTITION BY country ORDER BY revenue DESC, stock_code)`. Khoá phụ
   `stock_code` làm thứ tự xác định (deterministic): không có nó, hai mặt hàng hoà có thể đổi chỗ giữa hai lần
   chạy. `share = revenue / sum(revenue) OVER (PARTITION BY country)` tính ở cùng bước, trước khi lọc.
4. Lọc `rnk <= 3` ở ngoài (hoặc `QUALIFY`).

**Chọn hàm xếp hạng** theo câu hỏi business:

| Hàm | Hai mặt hàng hoà hạng 3 | Dùng khi |
| --- | --- | --- |
| `row_number()` | một cái hạng 3, một cái hạng 4 | cần **đúng N dòng** (slot trên dashboard, danh sách nhập hàng) |
| `rank()` | cả hai hạng 3, cái sau là 5 | "top 3" nghĩa là "không bỏ sót ai ngang hạng"; số dòng có thể > N |
| `dense_rank()` | cả hai hạng 3, cái sau là 4 | xếp **mức** (top 3 mức doanh thu), số dòng còn lớn hơn nữa |

### `pareto.sql`

- Luỹ kế với frame `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. Mặc định khi có `ORDER BY` là
  `RANGE ... CURRENT ROW`: các dòng **ngang giá trị** được coi là "cùng vị trí", nên hai mặt hàng cùng 20 GBP đều
  nhận luỹ kế đã cộng cả hai. Thêm `stock_code` vào `ORDER BY` cũng làm thứ tự duy nhất, nhưng ghi `ROWS` rõ
  ràng là thói quen tốt.
- `sum(revenue) OVER ()` (cửa sổ rỗng) là tổng toàn bảng, không cần subquery.
- Nhóm theo luỹ kế **trước** mặt hàng (`running - revenue`): mặt hàng làm tổng vượt 80% vẫn thuộc A. Quy ước khác
  (theo luỹ kế sau) cũng gặp; quan trọng là ghi rõ trong báo cáo và dùng một quy ước cho mọi kỳ.

## Con số trên bộ thật (12/2010 - 11/2011, chỉ hàng hoá)

- Doanh thu hàng hoá 9 655 544.63 GBP trên tổng 10 027 891.86 GBP (phí và điều chỉnh khoảng 372 nghìn).
- 38 nước, 114 dòng top 3. Mặt hàng số 1: UK `22423` REGENCY CAKESTAND 3 TIER (137 735.07, **1.7%** doanh thu
  hàng hoá UK), Germany cũng `22423` (8 310.15, 4.2%), France `23084` RABBIT NIGHT LIGHT (6 767.20, 3.8%),
  Netherlands `22326` ROUND SNACK BOXES SET OF4 WOODLAND (7 746.60, 2.8%).
- Pareto: 3 897 mặt hàng; **834 mặt hàng (21%) làm ra 80%** doanh thu hàng hoá, nhóm B 977, nhóm C 2 086 mặt hàng
  chỉ làm 5%. Gần đúng "luật 80/20".

## Đáp án trắc nghiệm

- **fee-top1 (c)**: 18 nước. UK đứng đầu là `DOT` (186 376 GBP), Germany, France, Spain, Belgium... là `POST`,
  Singapore, Hong Kong, Portugal là `M`. Báo cáo "sản phẩm bán chạy nhất ở Đức là phí gửi hàng" là lỗi định nghĩa,
  không phải insight.
- **uk-top-share (a)**: 1.7%. UK có hàng nghìn mặt hàng, doanh thu rất phân tán; top 3 cộng lại chỉ khoảng 4%.
- **class-a-count (b)**: 834 mặt hàng, 21% danh mục.
- **rank-rows (b)**: 121 dòng: ở vài nước nhỏ có nhiều mặt hàng hoà doanh thu quanh hạng 3, `rank` giữ tất cả.
  `rank` không bao giờ cho ít dòng hơn `row_number`.
- **jar-outlier (b)**: hoá đơn 541431 (khách 12346, 18/01/2011 10:01) mua 74 215 cái × 1.04 = 77 183.60 GBP,
  bị huỷ bằng C541433 lúc 10:17. Định nghĩa doanh thu gộp của track giữ dòng mua này. Xếp hạng sản phẩm để quyết
  định nhập hàng thì nên loại các cặp mua/huỷ như vậy hoặc xếp theo số khách mua; ít nhất phải ghi chú.
- **share-before-filter (b)**: chia cho tổng của 3 dòng thì 3 tỉ trọng luôn cộng bằng 100%; UK sẽ trông như
  "22423 chiếm 42%" thay vì 1.7%.
- **rows-vs-range (a)**: frame mặc định `RANGE` gộp các dòng ngang giá trị.
- **abc-use (b)**: nhóm C có thể là hàng mới ra (chưa đủ thời gian), hàng mùa vụ (chỉ bán tháng 11-12), hoặc hàng
  khách mua kèm hàng A (cắt đi làm mất đơn A). ABC theo doanh thu là điểm bắt đầu, không phải quyết định.

## Sai lầm hay gặp

- Xếp hạng trước khi gom về grain mặt hàng.
- `WHERE rnk <= 3` cùng cấp với window: lỗi "window functions are not allowed in WHERE".
- Lọc kỳ bằng `invoice_date <= '2011-11-30'`: mất mọi dòng ngày 30/11 sau 00:00.
