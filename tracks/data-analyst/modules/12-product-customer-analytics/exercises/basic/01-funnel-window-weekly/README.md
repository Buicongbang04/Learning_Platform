---
title: Funnel theo tuần có cửa sổ chuyển đổi và cờ "chưa chín" trên log Retailrocket
level: basic
services: []
files:
  - path: starter/funnel_window.ipynb
    note: 4 hàm TODO + đọc chart
  - path: tests/test_funnel_window.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py ecommerce-events
  - uv run jupyter lab tracks/data-analyst/modules/12-product-customer-analytics/exercises/basic/01-funnel-window-weekly/starter/funnel_window.ipynb
  - uv run pytest tracks/data-analyst/modules/12-product-customer-analytics/exercises/basic/01-funnel-window-weekly -q
---

## Mục tiêu

Biến một log sự kiện thô thành con số funnel mà PM đọc mỗi tuần mà không tự lừa mình: chọn cửa sổ chuyển đổi từ
phân phối thời gian tới khi mua, tính tỉ lệ theo tuần vào, và đánh dấu tuần chưa đủ thời gian quan sát.

## Đề bài

PM hỏi: **"Tuần trước bao nhiêu % người xem đã mua, và tỉ lệ đó đang tốt lên hay xấu đi?"**. Dữ liệu là bộ
`ecommerce-events` (Retailrocket, bản làm sạch): 2 755 641 sự kiện `view` / `addtocart` / `transaction` của
1 407 580 visitor, 03/05 tới 18/09/2015. Giấy phép gốc CC BY-NC-SA 4.0: chỉ dùng để học, không đưa trích mẫu lên
repo. Module 03 đã dựng funnel này bằng SQL; bài này làm bằng pandas và đi tiếp sang chiều thời gian. Mở
`starter/funnel_window.ipynb`:

1. `to_events(raw)`: đổi bảng CSV (`timestamp` epoch mili giây, `visitorid`, `event`, `itemid`) thành bốn cột
   `visitor_id`, `event`, `item_id`, `event_time`.
2. `ordered_first_times(events)`: mỗi visitor có `view` một dòng, cột `t_view`, `t_cart`, `t_buy` là mốc đầu tiên
   của từng bước **theo thứ tự** (giỏ tính từ lần xem đầu, mua tính từ lần thêm giỏ đầu).
3. `conversion_within(ft, hours)`: trong số người mua, tỉ lệ mua trong `h` giờ kể từ lần xem đầu.
4. `weekly_funnel(ft, window, data_end)`: theo tuần của lần xem đầu (bắt đầu thứ Hai): `visitors`, `cart_rate`,
   `buy_rate` trong cửa sổ, và `mature` khi `tuần + 7 ngày + window <= data_end`.
5. Chạy các cell vẽ: phân phối thời gian tới khi mua (trục log), buy rate theo tuần với cửa sổ 1, 7, 30 ngày và
   không cửa sổ, funnel theo sản phẩm. Đọc theo câu hỏi cuối notebook. Báo cáo bài học: làm phần trắc nghiệm trong
   app sau khi chạy notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên log nhỏ sinh trong test pass: giỏ trước lần xem đầu không tính, mua trước lần thêm giỏ đầu không tính,
  đúng 24 giờ vẫn tính là "trong 24 giờ", tuần bắt đầu thứ Hai, cờ `mature` đổi khi `data_end` đổi.
- Trên log thật: 1 404 179 → 32 934 → 9 952 visitor; 88.6% người mua mua trong 7 ngày; 21 tuần, 19 tuần đã chín;
  tuần cuối có 32 823 visitor và buy rate 0.49%.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`events[events.event == "view"].groupby("visitor_id").event_time.min()` cho `t_view`. Để lọc giỏ "vào hoặc sau"
lần xem đầu, `join` `t_view` vào các dòng `addtocart` theo `visitor_id` rồi so cột thời gian; `how="inner"` bỏ luôn
visitor không có lần xem nào.

### Gợi ý 2

`(ft.t_buy - ft.t_view) <= window` cho `False` ở dòng `NaT`, nên `.mean()` theo nhóm là tỉ lệ trên mọi visitor của
tuần. Tuần: `ft.t_view.dt.to_period("W-SUN").dt.start_time` (period kết thúc Chủ nhật, bắt đầu thứ Hai). Để
`groupby` nhận một Series làm khoá, đặt tên cho nó (`.rename("week")`).
