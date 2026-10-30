---
title: Funnel có thứ tự theo visitor và theo phiên từ log sự kiện thật, kèm memo cho PM
level: advanced
services: []
files:
  - path: starter/visitor_funnel.sql
    note: Funnel view -> giỏ -> mua theo visitor, có thứ tự
  - path: starter/session_funnel.sql
    note: Chia phiên 30 phút bằng window function, funnel trong phiên
  - path: starter/MEMO.md
    note: Memo 200-600 từ cho PM
  - path: starter/run_query.py
    note: Chạy thử SQL trên dữ liệu thật, không cần sửa
  - path: tests/test_funnel.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py ecommerce-events
  - uv run python tracks/data-analyst/modules/03-sql-for-analysts/exercises/advanced/02-event-funnel/starter/run_query.py visitor_funnel.sql
  - uv run pytest tracks/data-analyst/modules/03-sql-for-analysts/exercises/advanced/02-event-funnel -q
---

## Mục tiêu

PM checkout hỏi: **"Tỉ lệ chuyển đổi của mình là bao nhiêu, và nên tối ưu bước nào trước?"**. Bài này dựng
funnel từ log sự kiện thô bằng SQL theo hai cách đếm mà DA hay phải giải thích (theo người và theo phiên), xử lý
thứ tự sự kiện, chia phiên (sessionization) bằng window function, rồi biến số liệu thành một khuyến nghị.

## Đề bài

Bộ `ecommerce-events`: sự kiện web thật của một cửa hàng online (Retailrocket, bản làm sạch), 2 755 641 sự kiện của
1 407 580 visitor từ 03/05/2015 tới 18/09/2015. Giấy phép gốc CC BY-NC-SA 4.0: chỉ dùng để học, không đưa trích mẫu
lên repo. Test nạp bảng `events`:

| Cột | Kiểu | Ghi chú |
| --- | --- | --- |
| `visitor_id` | BIGINT | người dùng (cookie), không có phiên sẵn |
| `event` | VARCHAR | `view`, `addtocart`, `transaction` |
| `item_id` | BIGINT | mặt hàng |
| `event_time` | TIMESTAMP | UTC, tới mili giây |
| `transaction_id` | VARCHAR | chỉ có ở `transaction` |

Mỗi tệp là **một** câu `SELECT`, trả đúng ba dòng `(1, 'view')`, `(2, 'addtocart')`, `(3, 'transaction')` với cột
`step, event`, số đếm, `conv_from_prev` (so với bước trước, `NULL` ở bước 1) và `conv_from_first` (so với bước 1),
tỉ lệ làm tròn 4.

1. **`visitor_funnel.sql`** (cột đếm `visitors`): bước 1 là visitor có ít nhất một `view`; bước 2 là visitor có
   `addtocart` **vào hoặc sau** lần `view` đầu tiên; bước 3 là visitor có `transaction` vào hoặc sau lần
   `addtocart` đầu tiên tính ở bước 2. Không xét mặt hàng.
2. **`session_funnel.sql`** (cột đếm `sessions`): chia sự kiện của mỗi visitor thành phiên: sự kiện đầu mở phiên,
   sự kiện cách sự kiện trước của cùng visitor **hơn** 30 phút mở phiên mới (đúng 30 phút vẫn cùng phiên). Cùng
   quy tắc thứ tự như câu 1, nhưng mọi bước phải nằm trong **cùng một phiên**; bước 1 là số phiên có `view`.
3. **`MEMO.md`** cho PM theo khung có sẵn (200-600 từ, headline có con số, có tỉ lệ dạng %). Được viết thêm
   truy vấn phụ (thời gian từ xem tới mua, funnel theo tháng...) trong `starter/`, không chấm.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: thêm giỏ trước khi xem không tính, mua ở phiên khác không tính trong funnel theo phiên,
  khoảng cách 31 phút tách phiên còn 30 phút thì không, visitor chỉ có `transaction` không vào funnel.
- Trên bộ thật: theo visitor 1 404 179 → 32 934 → 9 952; theo phiên 1 755 781 → 36 677 → 10 722.
- `MEMO.md` không còn TODO, đủ mục. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Funnel có thứ tự: một CTE cho mỗi bước, mỗi CTE giữ mốc thời gian của bước đó.
`v` = `min(event_time)` của `view` theo visitor; `c` = join `v` với `events` (`event = 'addtocart' AND event_time >=
t_view`), lấy `min`; `p` tương tự từ `c`. Ba số đếm ghép bằng `UNION ALL`, tỉ lệ bằng `lag` và `first_value`.

### Gợi ý 2

Sessionization: `lag(event_time) OVER (PARTITION BY visitor_id ORDER BY event_time)`; cờ `new_session = 1` khi
`lag` là `NULL` hoặc `event_time - lag > INTERVAL 30 MINUTE`; `session_no` = tổng luỹ kế của cờ theo visitor
(`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`). Sau đó làm như câu 1 với khoá `(visitor_id, session_no)`.
