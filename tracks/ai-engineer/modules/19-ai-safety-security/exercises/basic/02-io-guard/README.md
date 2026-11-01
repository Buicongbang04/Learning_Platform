---
title: Guardrail tự viết cho input và output - chuẩn hoá chống lách, lọc link, kiểm tool
level: basic
services: []
files:
  - path: starter/guard.py
    note: 6 hàm TODO
  - path: tests/test_guard.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/19-ai-safety-security/exercises/basic/02-io-guard -q
---

## Mục tiêu

Viết các ràng buộc input/output bằng code, trước khi dùng thư viện guardrail nào: danh sách chặn không bị lách bằng
chữ hoa, chữ toàn khổ, ký tự vô hình, chữ Cyrillic giống Latin hay chữ cách quãng; bộ lọc link chặn kênh rò rỉ dữ
liệu qua ảnh markdown; và bộ kiểm lời gọi tool theo nguyên tắc least privilege. Bạn cũng thấy rõ giới hạn: danh sách
chặn chỉ bắt được cụm bạn đã nghĩ tới (mục 7 lý thuyết).

## Đề bài

**Phần cứng:** CPU · ~75 phút

Trong `starter/guard.py`, chỉ dùng thư viện chuẩn:

1. `normalize(text)`: lần lượt NFKC (chữ toàn khổ `ｉ` thành `i`); bỏ mọi ký tự thuộc nhóm Unicode `Cf` (zero-width,
   ký tự đảo chiều); `casefold`; đổi chữ theo bảng `CONFUSABLES`; `đ` thành `d`; tách dấu (NFD) và bỏ mọi ký tự nhóm
   `Mn`; mọi chuỗi ký tự không thuộc `a-z0-9` thành **một** dấu cách; bỏ dấu cách hai đầu.
2. `find_denied(text, phrases)`: các cụm của `phrases` (giữ thứ tự của `phrases`) xuất hiện trong `text`. So khớp trên
   bản đã `normalize` của cả hai, với hai quy tắc: giữa **hai ký tự liên tiếp bất kỳ** của cụm (đã bỏ dấu cách) được có
   hoặc không có một dấu cách, nên `i g n o r e` và `ignore-previous` đều khớp; hai đầu cụm phải là ranh giới (không có
   chữ hay số đứng sát), nên `system prompts` không khớp `system prompt`.
3. `check_input(text, *, max_chars, deny) -> Verdict`: lý do theo thứ tự `"empty"` (sau `normalize` không còn gì),
   `"too_long"` (`len(text) > max_chars`, tính trên chuỗi gốc), rồi `"denied:<cụm>"` cho từng cụm bị chặn;
   `allowed` là không có lý do nào.
4. `host_allowed(url, allowed)`: URL chứa dấu `\`, khoảng trắng, ký tự điều khiển (nhóm `Cc`) hoặc ký tự vô hình (nhóm
   `Cf`) thì `False` ngay. Còn lại lấy **hostname** bằng `urlsplit` (không phải chuỗi giữa `//` và `/`: phần `user@` và
   `:cổng` không phải host), bỏ dấu chấm cuối, chữ thường; đúng khi host bằng một tên miền trong `allowed` hoặc kết thúc
   bằng `"." + tên miền`. URL không parse được thì `False`.
5. `sanitize_links(reply, allowed) -> (reply_mới, removed)`:
   - link markdown `[chữ](url)` tới host lạ: giữ `chữ`, bỏ link;
   - ảnh markdown `![chữ](url)` tới host lạ: bỏ **cả cụm** (trình duyệt tự tải ảnh, URL ảnh là kênh gửi dữ liệu ra
     ngoài không cần người dùng bấm);
   - autolink `<http...>` và URL trần (`http://`, `https://`, `www.`, kể cả khi dính liền sau một chữ khác) tới host
     lạ: thay bằng `[link đã bị xoá]`;
   - URL không có scheme thì thêm `http://` trước khi kiểm host; `removed` là các URL đã xoá theo thứ tự xử lý.
6. `check_tool_call(call, policy) -> list[str]`: `call` là `{"name": ..., "arguments": {...}}`, `policy` ánh xạ tên
   tool tới luật từng tham số (`pattern`: chuỗi khớp **toàn bộ** regex; `enum`: nằm trong danh sách; `max`: số, không
   phải `bool`, không vượt `max`). Lỗi đúng chữ: `tool not allowed: <tên>` (dừng luôn), `arguments must be an object`
   (dừng luôn), `unknown argument: <k>`, `missing argument: <k>`, `<k>: not in allowed values`,
   `<k>: does not match pattern`, `<k>: above max or not a number`.

## Tiêu chí đạt

- Cụm bị chặn được nhận ra qua chữ hoa, xuống dòng, chữ toàn khổ, zero-width, Cyrillic, chữ cách quãng, gạch nối,
  ký tự đảo chiều, tiếng Việt có dấu, không dấu và NFD; câu bình thường chứa một phần của cụm không bị chặn.
- `host_allowed` đúng 16 ca, gồm tên miền giả dạng `congty.vn.evil.example`, `evilcongty.vn`, `congty.vn@evil.example`,
  và URL có `\`, tab hay ký tự vô hình.
- `normalize` bỏ ký tự vô hình, ký tự đảo chiều và tag characters (`U+E0000` tới `U+E007F`).
- `sanitize_links` xoá ảnh, link, autolink, URL trần, cả link kiểu tham chiếu `[1]: https://...`; giữ nguyên link được
  phép và văn bản không có link.
- `check_tool_call` chặn 11 lời gọi sai (tool lạ, email ngoài miền, xuống dòng chèn `bcc`, tham số thừa, thiếu tham
  số, vượt hạn mức, `True` thay số, sai đơn vị tiền) với đúng thông báo lỗi.

## Gợi ý

### Gợi ý 1

`unicodedata.category(ch)` trả mã nhóm như `"Cf"`, `"Mn"`. `str.translate` với bảng `CONFUSABLES` có sẵn. Cho quy
tắc "được có hoặc không có một dấu cách", dựng regex từ chính cụm: nối các ký tự (đã `re.escape`) bằng `" ?"`, thêm
lookbehind và lookahead âm cho ranh giới.

### Gợi ý 2

Chạy ba lượt thay thế theo thứ tự: markdown trước (để URL trong `(...)` không bị lượt URL trần cắt mất ngoặc), rồi
autolink, rồi URL trần. Trong hàm thay thế, quyết định giữ hay xoá bằng `host_allowed`, và ghi URL bị xoá vào một list
bên ngoài. Python coi `True` là `int`: loại riêng `bool` trước khi so với `max`.
