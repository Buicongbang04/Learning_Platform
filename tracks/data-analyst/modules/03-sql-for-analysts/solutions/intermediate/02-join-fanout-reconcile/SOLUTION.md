# Lời giải: join nhân bản doanh thu, NULL làm rơi dòng, reconcile

> `starter/run_query.py` là helper để chạy thử SQL trên dữ liệu thật, không được chấm và không có bản lời giải: giữ nguyên.

## Cách làm

### Bước 0: biết grain trước khi join

```sql
SELECT count(*), count(DISTINCT household_key) FROM campaign_table;   -- 7 208 dòng, 1 584 hộ
SELECT count(*), count(DISTINCT household_key) FROM hh_demographic;   -- 801, 801: khoá duy nhất
```

`campaign_table` có trung bình 4.6 dòng mỗi hộ (nhiều nhất 17), nên mỗi dòng giao dịch join theo
`household_key` thành 4-5 dòng. `hh_demographic` duy nhất theo hộ nên join không nhân bản, nhưng chỉ có 801/2 500
hộ, nên `INNER JOIN` **làm rơi** dòng.

### `fanout_audit.sql`

Hai CTE (`valid`, `naive`) và một `SELECT` các subquery vô hướng. Con số này là bằng chứng nên đưa vào ghi chú
review khi sửa báo cáo của người khác: "join thẳng nhân doanh thu lên 5.44 lần".

### `campaign_type_revenue.sql`

1. Gom doanh thu về grain **hộ** (`hh_revenue`).
2. Gom `campaign_table` về grain **(hộ, loại campaign)** bằng `SELECT DISTINCT` (hộ 1 nhận hai campaign TypeA chỉ
   còn một dòng TypeA).
3. `LEFT JOIN` từ `hh_type` sang `hh_revenue` (hộ nhận campaign mà không mua vẫn được đếm, doanh thu 0), cộng nhóm
   `None` bằng `NOT EXISTS`.

Bảng kết quả **không cộng dọc được**: một hộ nhận cả TypeA và TypeB có mặt ở hai dòng. Đây không phải lỗi mà là
bản chất câu hỏi "doanh thu của nhóm hộ nhận loại X"; phải ghi chú dưới bảng.

### `revenue_by_income.sql`

Gom về hộ, `LEFT JOIN hh_demographic`, `coalesce(INCOME_DESC, 'Unknown')`. `sum(sum(revenue)) OVER ()` là tổng
của các nhóm (window chạy sau `GROUP BY`).

### `reconcile.sql`

Mỗi phép kiểm một dòng với `expected` lấy từ bảng gốc và `actual` lấy từ cách tính của báo cáo. Đây là mẫu nên
giữ cạnh mọi báo cáo quan trọng: chạy lại mỗi lần sửa truy vấn, và trong dbt thì thành test.

## Con số trên bộ thật

| Đại lượng | Giá trị |
| --- | --- |
| Dòng hợp lệ / sau join thẳng | 2 576 815 / 13 919 433 (**5.40 lần**) |
| Doanh thu thật / sau join thẳng | 8 057 443.80 / 43 835 274.72 (**5.44 lần**) |
| Báo cáo thu nhập dùng INNER JOIN | 801 hộ, 4 497 711.61 GBP, **55.8%** doanh thu |
| `Unknown` | 1 699 hộ (68%), 3 559 732.19 (**44.2%**) |
| Nhóm thu nhập lớn nhất có thông tin | `50-74K`: 192 hộ, 1 094 850.89 (13.6%) |

| `campaign_type` | Hộ | Doanh thu | Doanh thu / hộ |
| --- | --- | --- | --- |
| None | 916 | 942 143.58 | 1 028.54 |
| TypeA | 1 513 | 6 935 414.78 | 4 583.88 |
| TypeB | 1 023 | 5 672 399.85 | 5 544.87 |
| TypeC | 397 | 2 856 103.03 | 7 194.21 |

1 584 hộ nhận ít nhất một campaign (63% số hộ) làm ra 7 115 300.22, tức **88%** doanh thu.

## Đáp án trắc nghiệm

- **inflation (c)**: 5.44 lần.
- **unknown-share (a)**: 44.2%. Báo cáo "theo thu nhập" mà bỏ nhóm này là báo cáo về 56% doanh thu.
- **inner-coverage (d)**: 55.8%. Mọi tỉ trọng trong báo cáo INNER JOIN đều tính trên mẫu số sai; phương án "hơn 100%"
  sai vì `hh_demographic` duy nhất theo hộ, không nhân bản.
- **per-household (b)**: **selection bias**. Campaign được gửi tới hộ đã chọn trước (thường là hộ mua nhiều): 1 584
  hộ nhận campaign làm ra 88% doanh thu. So hộ nhận với hộ không nhận là so hai nhóm khác nhau từ đầu. Muốn đo hiệu
  quả cần so trước/sau trong cùng nhóm hộ, nhóm đối chứng, hoặc thiết kế thí nghiệm (module 11, capstone M6).
- **sum-over-types (a)**: 942 143.58 + 6 935 414.78 + 5 672 399.85 + 2 856 103.03 = 16 406 061.24. Mỗi dòng đúng;
  cộng dọc thì sai. Ghi rõ dưới bảng: "một hộ có thể thuộc nhiều nhóm, không cộng các dòng".
- **detect-fanout (d)**: khoá không duy nhất ở bảng được join là dấu hiệu nhân bản. Thêm `DISTINCT` ở cuối
  che triệu chứng ở phép đếm nhưng không sửa tổng.
- **distinct-hides (b)**: `count(DISTINCT)` đếm đúng hộ, còn `sum(SALES_VALUE)` cộng mọi dòng đã nhân. Bảng sai
  trông "hợp lý" vì cột số hộ đúng.
- **not-in-null (c)**: `x NOT IN (..., NULL)` là `x <> a AND ... AND x <> NULL`; `x <> NULL` là `NULL` nên cả biểu
  thức không bao giờ `TRUE`. `campaign_table` thật không có NULL, nhưng đây là lý do mặc định dùng `NOT EXISTS`.

## Sai lầm hay gặp

- Sửa join nhân bản bằng `SELECT DISTINCT` trên dòng giao dịch: hai dòng mua thật giống nhau (cùng hộ, cùng giá)
  bị gộp làm một.
- Lọc bảng bên phải của `LEFT JOIN` trong `WHERE` (`WHERE d.INCOME_DESC <> 'Under 15K'`): hộ `NULL` bị loại, `LEFT
  JOIN` thành `INNER JOIN`. Đặt điều kiện vào `ON` hoặc xử lý `NULL` rõ ràng.
- Báo cáo tỉ trọng mà không báo mẫu số (tổng doanh thu, số hộ) cạnh bảng: người đọc không phát hiện được dòng bị rơi.
