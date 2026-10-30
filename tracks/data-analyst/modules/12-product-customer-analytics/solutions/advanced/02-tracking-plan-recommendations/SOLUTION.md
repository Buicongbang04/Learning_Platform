# Hướng làm: tracking plan cho khối "Thường mua kèm"

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết validator, một plan mẫu, các quyết định cần cân nhắc
và rubric chấm `tracking_plan.yaml` cùng `PLAN.md`.

## Validator

- Gộp quy tắc: `spec = {**common_properties, **events[name]["properties"]}`. Sự kiện lạ trả ngay `["unknown_event"]`
  (không kiểm tiếp: mọi thuộc tính sẽ thành "thừa", làm nhiễu báo cáo).
- Với từng quy tắc: giá trị `None` hoặc không có → `missing` nếu `required`; có giá trị thì kiểm kiểu, đúng kiểu mới
  kiểm `enum` (một giá trị sai kiểu chỉ báo một lỗi).
- Kiểu: `integer` là `int` nhưng **không** `bool` (`isinstance(True, int)` là `True`); `number` nhận `int` và
  `float`, không nhận `bool`; `timestamp` là chuỗi `datetime.fromisoformat` đọc được (Python 3.11+ nhận cả `Z`).
- Thuộc tính đã gửi mà không có trong `spec` → `extra`. Trả `sorted(issues)` để kết quả ổn định.
- `validate_log`: danh sách `(event, issue)`, `DataFrame(...).value_counts()`, sắp theo `count` giảm dần rồi `event`,
  `issue`; không có lỗi thì bảng rỗng đúng ba cột.

## Plan mẫu (rút gọn)

| Sự kiện | Trigger | Thuộc tính chính | Metric |
| --- | --- | --- | --- |
| `recommendation_shown` | Client, khối hiện ≥ 50% trong viewport ≥ 1 giây, một lần mỗi lượt xem trang | `item_id`, `recommended_item_ids` (array), `source` (enum `basket_rules`, `bestseller_fallback`), `rule_version`, `variant` (enum) | CTR, độ phủ |
| `recommendation_clicked` | Client, bấm một sản phẩm trong khối | `item_id`, `recommended_item_id`, `position` (integer), `source`, `variant` | CTR |
| `cart_item_added` | Server, API thêm giỏ trả 200 | `item_id`, `quantity`, `price`, `add_source` (enum `product_page`, `recommendation`, `search`, `listing`), `recommended_from_item_id` | Attach rate, doanh thu mỗi người xem |
| `order_completed` | Server, thanh toán xác nhận | `order_id`, `revenue`, `item_ids`, `recommended_item_ids_in_order` | Doanh thu mỗi người xem, AOV |

Thuộc tính chung: `anonymous_id`, `session_id` (client sinh), `event_time` (UTC), `user_id` (tuỳ chọn), `platform`
(enum), `app_version`.

Metric chính: doanh thu mỗi visitor có `recommendation_shown` trong 7 ngày, treatment so với control. Phụ: CTR, attach
rate. Guardrail: AOV, tỉ lệ thoát, thời gian tải trang.

## Các quyết định cần cân nhắc

- **Impression**: "render" làm CTR thấp giả (khối ở cuối trang không ai cuộn tới); "trong viewport" cần thêm logic ở
  client. Ghi rõ, và không đổi định nghĩa sau ra mắt mà không đổi version.
- **Nhóm control cũng phải có sự kiện**: control không thấy khối, nên cần một sự kiện "đủ điều kiện hiện khối" (hoặc
  ghi `variant` trên mọi lượt xem trang sản phẩm), nếu không không có mẫu số cho nhóm control. Plan mẫu ở trên dùng
  `recommendation_shown` cho cả hai nhóm (control: khối được tính toán nhưng không hiện) là một cách; cách khác là
  `product_viewed` có `variant`. Người làm bài nêu được vấn đề này là điểm cộng lớn.
- **Gắn đơn hàng với gợi ý**: `add_source` trên thêm giỏ và danh sách mã được gợi ý trong đơn, thay vì đoán từ thứ tự
  sự kiện. Đây chính là thứ log Retailrocket thiếu (565 sản phẩm có người mua nhiều hơn người thêm giỏ).
- **Phân khúc**: phân khúc RFM tính tại ngày ra mắt, nối qua `user_id` (khách đăng nhập); khách ẩn danh là một phân
  khúc riêng. Khách sỉ (champions) có thể đã tự mua đủ bộ: uplift có thể gần 0 dù CTR cao.
- **Dữ liệu cá nhân**: không email, số điện thoại, tên; `user_id` là mã nội bộ.
- **QA**: chặn ra mắt khi còn lỗi `missing`, `type`, `unknown_event` trên staging; thêm kiểm số lượng (impression so
  với lượt xem trang, `order_completed` so với bảng đơn hàng).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Metric từ câu hỏi | 20 | Một metric chính đo doanh thu/giá trị (không chỉ CTR), có tử số, mẫu số, cửa sổ, đơn vị đếm; có guardrail |
| Sự kiện và trigger | 20 | Đủ sự kiện để tính mọi metric; trigger rõ (viewport, server khi giao dịch); có cách gắn đơn hàng với gợi ý |
| Thiết kế A/B | 15 | `variant` có trong dữ liệu; nêu mẫu số cho nhóm control |
| Thuộc tính và kiểu | 15 | Kiểu đúng, enum cho tập giá trị cố định, định danh đủ (anonymous, user, session), không có dữ liệu cá nhân |
| Phân tích phân khúc | 15 | Phân khúc định nghĩa trước khi xem kết quả, có thuộc tính để tách, nêu một kết quả có thể đổi quyết định |
| QA và rủi ro | 15 | Ngưỡng chặn ra mắt, người sửa, kiểm số lượng; bot, trùng, version, chi phí sự kiện |

Từ 70 điểm trở lên là plan đưa được cho engineering instrument.

## Sai lầm hay gặp

- "Ghi hết cho chắc": hàng chục sự kiện không phục vụ metric nào, không có owner.
- Chỉ đo CTR: khối gợi ý có thể được bấm nhiều mà không tăng doanh thu (khách bấm vì tò mò, hoặc mua món họ đã định mua).
- Tên lệch nhau giữa nền tảng (`AddToCart`, `add_to_cart`, `cart_add`): một tên, một quy ước, kiểm tự động.
- Không có `variant` trong sự kiện, phải nối bảng phân nhóm sau: nối sai là kết quả A/B sai.
