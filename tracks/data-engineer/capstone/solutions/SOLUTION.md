# Lời giải tham chiếu: notebook khám phá Olist thật

Capstone không có `starter/`/`solutions/` như bài tập: người học làm thẳng trong
`project/notebooks/olist_exploration.ipynb` và `project/notebooks/report.md`. Thư mục này giữ bản tham chiếu
để kiểm các con số ghim trong `project/tests/test_olist_exploration.py`:

```bash
uv run pytest tracks/data-engineer/capstone/project/tests -q -rs              # notebook của bạn (hàm TODO thì skip)
SOLUTION=1 uv run pytest tracks/data-engineer/capstone/project/tests -q       # bản tham chiếu, phải pass hết
```

Chỉ mở sau khi đã tự làm. Cả notebook chạy khoảng 4 giây.

## Cách làm

1. **clean_orders**: so `.dt.normalize()` của ngày giao và ngày dự kiến để ra `delay_days` theo ngày lịch;
   `.where(is_delivered)` để đơn chưa giao là `<NA>`; `Int64`/`boolean` là kiểu nullable của pandas, giữ được
   "không biết" thay vì ép thành 0/`False`.
2. **dedup_reviews**: `sort_values` theo khoá + thời gian trả lời, `drop_duplicates("order_id", keep="last")`.
3. **build_order_facts**: `groupby("order_id").agg(...)` cho items và payments **trước**, rồi `merge(...,
   validate="one_to_one")` vào orders. `fillna(0)` cho tiền/số item của đơn không có item/payment.
4. **Phân tích**: mỗi câu hỏi một hàm trả bảng nhỏ (`review_by_delay` dùng `pd.cut` với `observed=False` để giữ
   đủ 5 nhóm kể cả nhóm rỗng), `insights` chỉ gom lại.
5. **write_clean**: ghi tệp tạm trong cùng thư mục rồi `os.replace` (nguyên tử trên cùng filesystem).

## Con số tham chiếu (bộ thật)

| Đại lượng | Giá trị |
| --- | --- |
| Đơn / đơn đã giao (`is_delivered`) | 99 441 / 96 470 |
| Tỉ lệ trễ / trung vị ngày giao | 0,0677 / 10,22 ngày |
| Review TB đúng hạn vs trễ | 4,290 vs 2,270 (1–2 sao: 0,0927 vs 0,6242) |
| `review_by_delay` số đơn | 75 744 · 12 419 · 1 280 · 3 600 · 2 781 (TB 4,31 · 4,18 · 4,03 · 2,71 · 1,70) |
| Bang trễ nhất (≥ 100 đơn) | AL 0,2141 |
| Thanh toán | `credit_card` 0,7694 số đơn; trả góp 0,6685 lần trả bằng thẻ |
| 10% seller lớn nhất | 0,6756 GMV |
| Danh mục đầu | `health_beauty` 1 258 681,34 |
| Khách mua lại | 0,0304 |
| `bad_timeline` / đơn có review / tổng `items_value` | 189 / 98 673 / 13 591 643,70 |

## Rubric cho báo cáo

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Bộ dữ liệu | nguồn, giấy phép, số dòng | thêm grain từng bảng, `customer_id` vs `customer_unique_id`, tháng bị cắt |
| Làm sạch | liệt kê bất thường và cách xử lý | giải thích vì sao gắn cờ thay vì xoá, chứng minh join không nhân tiền |
| Insight | ≥ 3 phát hiện có số | mỗi số kèm hệ quả cho nền tảng (KPI dashboard, rule chất lượng, SCD2, bộ lọc) |
| Giới hạn | nêu được mẫu ẩn danh, tháng cắt | nêu định nghĩa tự chọn làm số đổi, tương quan ≠ nhân quả |
