---
title: Tối ưu một pipeline pandas chậm
level: intermediate
services: []
files:
  - path: starter/report.ipynb
    note: 2 hàm TODO + ghi chú
  - path: tests/test_report.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/08-coding-for-ds/exercises/intermediate/03-pandas-optimization/starter/report.ipynb
  - uv run pytest tracks/data-science/modules/08-coding-for-ds/exercises/intermediate/03-pandas-optimization -q
---

## Mục tiêu

Viết lại một hàm pandas dùng `iterrows` thành bản vector hoá cho **cùng kết quả**, nhanh hơn hàng chục
lần, và giảm bộ nhớ bằng dtype. Đây là việc DS làm thường xuyên khi notebook phân tích bắt đầu chạy
hàng giờ.

## Đề bài

Mở `starter/report.ipynb`. Hàm `slow_seller_report(orders, items, reviews)` cho sẵn là **đặc tả**:
bảng điểm mỗi seller gồm `n_orders`, `revenue`, `late_rate`, `review_score`, `bad_review_rate` trên các
đơn giao xong (định nghĩa chi tiết trong docstring). Đừng sửa nó.

1. `fast_seller_report(orders, items, reviews)`: kết quả giống hệt bản chậm (cột, index, giá trị, NaN
   khi seller không có đơn nào có review), không lặp theo dòng, không `apply`, không sửa input.
2. `optimize_dtypes(df, max_unique_ratio=0.5)`: bản sao với cột chuỗi có `nunique / len < max_unique_ratio`
   thành `category`, cột số nguyên downcast về kiểu nhỏ nhất; float và datetime giữ nguyên.
3. Đo trên Olist thật (cell `explore`) và ghi 3–5 dòng nhận xét ở cell cuối.

## Tiêu chí đạt

- `fast_seller_report` khớp `slow_seller_report` trên dữ liệu tay và 3 bộ dữ liệu ngẫu nhiên.
- Mã của `fast_seller_report` không chứa `iterrows`, `itertuples`, `.apply(`, `axis=1`.
- Chạy xong 1 000 000 món hàng (800 000 đơn) trong 20 giây; bản `iterrows` cần vài phút.
- `optimize_dtypes` đúng kiểu từng cột, không đổi giá trị, giảm bộ nhớ ít nhất 25% trên dữ liệu test.
- Trên Olist thật: 2 970 seller, tổng `n_orders` 97 811, tổng `revenue` 13 220 248.93.

## Gợi ý

### Gợi ý 1

Chia nhỏ: (a) đơn giao xong kèm cột `late` từ so sánh hai cột datetime; (b) review mới nhất mỗi đơn:
`sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")`; (c) doanh thu: merge
`items` với đơn giao xong, `groupby("seller_id").price.sum()`.

### Gợi ý 2

Các tỉ lệ tính theo **đơn**, không theo món: `items[["seller_id", "order_id"]].drop_duplicates()`, merge
với (a) và (b) (`validate="many_to_one"` cho bảng review), rồi `groupby().agg(n_orders=("order_id",
"size"), late_rate=("late", "mean"), ...)`. Cột `bad` phải là NaN khi đơn không có review:
`(score <= 2).where(score.notna())`, để `mean` bỏ qua đúng các đơn đó.
