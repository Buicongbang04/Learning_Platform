---
title: Audit kho question Metabase self-serve và đề xuất quản trị
level: advanced
services: [metabase]
files:
  - path: starter/audit.py
    note: 3 TODO - chuẩn hoá tên, tìm lỗi, tổng hợp
  - path: starter/AUDIT_MEMO.md
    note: Memo phát hiện, đề xuất, kế hoạch 30 ngày
  - path: tests/test_audit.py
    note: Không sửa
  - path: tests/fixtures/cards.json
    note: Kho 10 card ví dụ giả định (không sửa)
run:
  - uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/advanced/02-self-serve-audit/starter/audit.py
  - uv run pytest tracks/data-analyst/modules/10-bi-dashboards/exercises/advanced/02-self-serve-audit -q
---

## Mục tiêu

Sáu tháng sau khi mở self-serve, Head of Data nhận phàn nàn: "trong cuộc họp có hai con số doanh thu tháng", "tôi
không biết question nào là chính thức". Bạn audit kho question Metabase bằng API, đo các lỗi quản trị hay gặp
(tên trùng, tự tính doanh thu, thiếu mô tả ở collection chính thức, card bỏ hoang), và viết đề xuất quản trị có
kế hoạch 30 ngày. Làm xong bạn biết self-serve thất bại ở đâu và cách đưa nó về một nguồn sự thật mà không cấm
người dùng tự hỏi.

## Đề bài

`tests/fixtures/cards.json` là **ví dụ giả định**: 10 card theo đúng cấu trúc `GET /api/card` của Metabase (tên,
`archived`, `description`, `dataset_query`, `collection` có `authority_level`, `created_at`, `last_used_at`), dựng
để có đủ các loại lỗi; con số trong đó không phải dữ liệu thật. Script cũng chạy trên Metabase thật của bạn nếu
BI đang bật.

Mở `starter/audit.py`, viết:

1. **`normalize_name(name)`**: chữ thường, bỏ dấu câu (`·`, `:`, `-`, ngoặc...), gộp khoảng trắng; giữ chữ có dấu
   tiếng Việt.
2. **`find_issues(cards, now, stale_days=90)`**: list `{"card_id", "issue", "detail"}` sắp theo
   `(card_id, issue)`, bỏ qua card đã archive, mỗi (card, loại lỗi) một dòng:
   - `duplicate_name`: từ 2 card trở lên cùng `normalize_name`; `detail` nêu id các card cùng tên;
   - `custom_revenue`: SQL native tự nhân `quantity * price` (hoặc `price * quantity`, mọi hoa thường, có hoặc
     không khoảng trắng) thay vì dùng cột `revenue` đã chuẩn hoá;
   - `no_description`: card trong collection có `authority_level` `"official"` mà `description` rỗng, `None` hoặc
     chỉ có khoảng trắng;
   - `stale`: `last_used_at` cũ hơn `now - stale_days`; chưa dùng lần nào (`None`) thì xét `created_at`.
     Thời gian dạng ISO `"2026-10-28T08:00:00Z"`.
3. **`summarize(issues)`**: `{issue: số card}`, khoá sắp theo tên.

Rồi viết **`starter/AUDIT_MEMO.md`** (giữ ba heading `## Phát hiện`, `## Đề xuất`, `## Kế hoạch 30 ngày`, 300-700
từ) gửi Head of Data: mỗi loại lỗi bao nhiêu card, ví dụ cụ thể và rủi ro cho người ra quyết định; đề xuất nguồn
chuẩn (model hoặc bảng đã làm sạch, metric định nghĩa một lần), collection official và ai được đưa card vào, quy
ước đặt tên và mô tả, quy trình archive có báo trước; kế hoạch 30 ngày với người làm và chỉ số đo thành công.

## Tiêu chí đạt

- Trên fixture (với `now` = 30/10/2026): tên trùng ở card 1, 2, 8 (card 3 cùng tên nhưng đã archive); tự tính
  doanh thu ở 2, 5, 9; thiếu mô tả ở 4, 10; bỏ hoang ở 5, 6 (với 30 ngày: 5, 6, 8, 10); tổng hợp
  `{"custom_revenue": 3, "duplicate_name": 3, "no_description": 2, "stale": 2}`.
- `find_issues` chạy được trên kho card thật của Metabase (question MBQL không có SQL, card không nằm trong
  collection nào).
- `AUDIT_MEMO.md` không còn TODO, đủ ba mục; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`re.sub(r"[^\w\s]", " ", name.lower())` giữ chữ có dấu (`\w` của Python hiểu Unicode) rồi
`" ".join(s.split())`. Gom card theo tên chuẩn hoá bằng một dict trước, rồi mới duyệt từng card để tạo lỗi.
`collection` có thể là `None` (card ở root) và `dataset_query` của question MBQL không có khoá `native`.

### Gợi ý 2

Regex `quantity\s*\*\s*price|price\s*\*\s*quantity` với `re.IGNORECASE`. Thời gian:
`dt.datetime.fromisoformat(s.replace("Z", "+00:00"))` (Python 3.11+ đọc được cả phần lẻ giây). Trong memo, đừng
dừng ở "xoá card trùng": card 2 có 37 lượt xem trong ví dụ, tức có người đang dùng nó; hỏi họ vì sao không dùng
card chính thức trước khi archive.
