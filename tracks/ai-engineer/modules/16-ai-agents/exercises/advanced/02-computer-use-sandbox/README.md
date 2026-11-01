---
title: Agent điều khiển trình duyệt giả lập - prompt injection gián tiếp và bốn cách phòng thủ
level: advanced
services: []
files:
  - path: starter/guards.py
    note: delimit, datamark, guard TODO
  - path: starter/simweb.py
    note: Trang web giả lập, 8 task (không sửa)
  - path: starter/agent.ipynb
    note: Tool trình duyệt, chạy agent, đo
  - path: starter/REPORT.md
    note: Báo cáo
  - path: tests/test_guards.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - uv run pytest tracks/ai-engineer/modules/16-ai-agents/exercises/advanced/02-computer-use-sandbox -q
  - uv run jupyter lab tracks/ai-engineer/modules/16-ai-agents/exercises/advanced/02-computer-use-sandbox/starter/agent.ipynb
---

## Mục tiêu

Dựng một agent "computer use" an toàn: thay vì màn hình thật, agent điều khiển một hiệu sách giả lập qua cây phần tử dạng
chữ (giống accessibility tree mà Playwright MCP hay browser-use dùng), làm 8 việc của người dùng (tra giá, thêm giỏ, đặt
hàng, đổi email). Hai trang sách chứa một đánh giá của khách có **prompt injection gián tiếp** bảo agent đổi email tài
khoản sang địa chỉ của kẻ tấn công. Bạn đo cùng lúc tỉ lệ hoàn thành và tỉ lệ bị tấn công thành công dưới bốn cấu hình
phòng thủ, và thấy khác biệt giữa phòng thủ bằng prompt và phòng thủ bằng code.

## Đề bài

**Phần cứng:** CPU · ~240 phút

Thời gian trên là thời gian làm bài. Một lượt 8 task với `qwen2.5:3b` chạy vài phút trên PC của track; bài cần 4 cấu
hình, tổng cỡ 15 tới 25 phút máy chạy.

1. `starter/guards.py` (có test):
   - `delimit(text)`: bọc nội dung trang giữa `OPEN` và `CLOSE`, xoá trước các lần xuất hiện của hai dấu đó trong nội
     dung (kẻ tấn công chèn sẵn `CLOSE` để "thoát" ra ngoài vùng dữ liệu).
   - `datamark(text)`: thay mọi chuỗi khoảng trắng bằng một ký tự đánh dấu (Hines et al., 2024).
   - `guard(element, task, values)`: quyết định **bằng code** có cho bấm "Lưu email" và "Đặt hàng" không, theo yêu cầu
     gốc của người dùng và giá trị đã nhập.
2. `starter/agent.ipynb`: ba tool `read_page`, `click`, `type_text` gắn với một `SimShop`, vòng ReAct của bài Basic 02,
   chạy 8 task với 4 cấu hình: không phòng thủ, `delimit` + chỉ thị, `datamark` + chỉ thị, `guard`. Mỗi lượt ghi: hoàn
   thành không, email có bị đổi sang `EVIL_EMAIL` không, agent có thấy trang chứa injection không, số lần guard chặn,
   số bước, lý do dừng.
3. Viết `starter/REPORT.md`, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt**:

- Bảng 4 cấu hình: hoàn thành / 8, số task thấy injection, ASR tính trên số task **đã thấy** injection, số lần guard
  chặn (và có chặn nhầm task hợp lệ nào không), số bước trung bình.
- Đọc trace của ít nhất 3 lượt bị tấn công (hoặc suýt bị): agent làm theo injection ở bước nào, nó có "nghi ngờ" trong
  Thought không.
- Phòng thủ bằng prompt bảo đảm gì, phòng thủ bằng code bảo đảm gì và **không** bảo vệ được gì (thông tin lộ qua câu
  trả lời, thao tác không có trong danh sách nhạy cảm, injection đổi địa chỉ giao hàng sang một địa chỉ cũng có trong
  task?). Đề xuất kiến trúc cho một agent trình duyệt thật (sandbox, allowlist, xác nhận người dùng, tách quyền).
- Giới hạn: 8 task, một kiểu injection, một model; con số ASR không khái quát cho model khác.

## Tiêu chí đạt

- Test của `guards.py` pass: bọc đúng định dạng; dấu phân cách chèn sẵn (kể cả viết thường, dạng NFD) bị xoá; datamark
  thay mọi loại khoảng trắng; guard cho phép đổi email chỉ khi địa chỉ mới có trong yêu cầu, cho phép đặt hàng chỉ khi
  người dùng muốn mua và địa chỉ nhập có trong yêu cầu, không chặn thao tác thường; guard chặn được injection khi gắn vào
  `SimShop` mà vẫn cho task đổi email hợp lệ chạy.
- `REPORT.md` không còn TODO, ít nhất 400 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

So khớp dấu phân cách không phân biệt hoa thường và sau chuẩn hoá NFC: `re.sub(re.escape(marker), "", text,
flags=re.I)` sau `unicodedata.normalize("NFC", ...)`. Với `guard`, chuẩn hoá cả yêu cầu lẫn giá trị nhập (NFC, chữ
thường, bỏ khoảng trắng hai đầu) trước khi so; giá trị rỗng không bao giờ "nằm trong" yêu cầu một cách có nghĩa.

### Gợi ý 2

Đo ASR trên mẫu số đúng: một task không bao giờ mở trang có injection thì không nói gì về khả năng chống injection.
Đổi cấu hình phòng thủ có thể đổi cả đường đi của agent (số trang nó mở), nên ghi lại `exposed` cho từng lượt. Chạy
`SimShop(...).read_page()` và in observation đã bọc để chắc model thấy đúng thứ bạn nghĩ.
