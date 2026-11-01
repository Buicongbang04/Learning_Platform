---
title: Phát hiện, che và giả danh hoá PII tiếng Việt
level: basic
services: []
files:
  - path: starter/pii.py
    note: 7 hàm và một lớp TODO
  - path: tests/test_pii.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/19-ai-safety-security/exercises/basic/01-pii-redaction -q
---

## Mục tiêu

Viết bộ lọc PII chạy trước mọi lời gọi LLM và mọi dòng log: tìm số CCCD/CMND, số điện thoại, email, số thẻ, số tài
khoản ngân hàng, địa chỉ trong văn bản tiếng Việt; che chúng đi, hoặc thay bằng token giả danh khôi phục được để
LLM vẫn làm việc với "khách hàng `<PHONE_...>`" và câu trả lời vẫn đưa lại đúng số cho nhân viên. Bạn thấy vì sao
regex cần **kiểm tra cấu trúc** (Luhn, mã tỉnh) và **ngữ cảnh** (từ khoá) mới đủ chính xác.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Trong `starter/pii.py`, chỉ dùng thư viện chuẩn (`re`, `hmac`, `hashlib`), viết:

1. `luhn_ok(digits)`: kiểm Luhn (mục 3 lý thuyết). `cccd_ok(digits)`: đúng 12 chữ số, 3 số đầu nằm trong
   `PROVINCE_CODES`, số thứ 4 (mã thế kỷ và giới tính: 0/1 sinh thế kỷ 20, 2/3 thế kỷ 21) trong `0..3`.
2. `find_pii(text) -> list[Span]`, mỗi `Span(start, end, kind, text)` với `text == text_gốc[start:end]`:
   - `EMAIL`: dạng `ten.ho+tag@ten-mien.com.vn`.
   - `PHONE`: di động Việt Nam, đầu `0`, `84` hoặc `+84`, rồi một chữ số trong `3 5 7 8 9` và 8 chữ số nữa; giữa các
     chữ số được có **một** dấu cách, chấm hoặc gạch (`0938 471 526`, `0938.471.526`, `+84 938 471 526`).
   - `CARD`: 13 tới 19 chữ số, có thể chia nhóm 4 bằng dấu cách hoặc gạch, **và** qua Luhn.
   - `CCCD`: 12 chữ số liền **và** qua `cccd_ok`.
   - `BANK`: 6 tới 19 chữ số (có thể có dấu cách, chấm, gạch xen giữa) đứng sau một từ khoá `số tài khoản`, `STK`,
     `tài khoản số`, `TK số`, `số TK` (không phân biệt hoa thường; cho phép `:`, `là`, `số` ở giữa). Span chỉ gồm
     phần số.
   - `CMND`: đúng 9 chữ số sau từ khoá `CMND`, `chứng minh nhân dân`, `số chứng minh`.
   - `ADDRESS`: `[số ]<số nhà>[/<số>...] <đường|phố|ngõ|hẻm|ngách> <tên>` rồi **ít nhất một** đơn vị hành chính
     `, <phường|xã|thị trấn|quận|huyện|thị xã|TP.|thành phố|tỉnh> <tên>`.
   - Một dãy số **không** được khớp nếu nó nằm trong một dãy số dài hơn (chữ số, hoặc dấu chấm/phẩy rồi chữ số, đứng
     ngay trước hay ngay sau): `1.093.847.152 đồng` không chứa số điện thoại.
   - Kết quả qua `resolve_overlaps`.
3. `resolve_overlaps(spans)`: hai span chồng lấn (có chung ít nhất một ký tự; chạm nhau ở biên thì không) thì giữ
   span **dài hơn**; dài bằng nhau thì loại đứng trước trong `KINDS` thắng (từ khoá thắng hình dạng: `STK 0938471526`
   là số tài khoản). Trả theo `start` tăng dần.
4. `redact(text, spans=None)`: thay mỗi span bằng `[KIND]`. Span truyền vào cũng qua `resolve_overlaps` trước.
5. `Pseudonymizer(key)`: khoá rỗng thì `ValueError`. `token(kind, value)` trả `<KIND_xxxxxxxxxx>` với 10 ký tự hex đầu
   của `HMAC-SHA256(key, f"{kind}:{chuẩn}")`, trong đó `chuẩn` là: số điện thoại về dạng `0` + 9 chữ số cuối; email
   và địa chỉ là chữ thường bỏ khoảng trắng hai đầu; loại khác là các chữ số. Ghi `vault[token] = giá trị gốc` (lần
   đầu gặp). `pseudonymize(text)` thay mọi PII bằng token; `restore(text)` thay token có trong `vault` về giá trị gốc,
   để nguyên token lạ.
6. `score(pred, gold)`: theo từng loại có trong `pred` hoặc `gold`: `tp`, `fp`, `fn`, `precision`, `recall`; đúng khi
   trùng cả `(start, end)`. Loại không có dự đoán nào thì `precision = 1.0`; không có gold thì `recall = 1.0`.

## Tiêu chí đạt

- Luhn, cấu trúc CCCD, 6 dạng số điện thoại, email, thẻ có và không có dấu cách, số tài khoản và CMND theo từ khoá,
  địa chỉ nhiều cấp đều khớp đúng span.
- Không khớp: số trong dãy dài hơn, số tiền có dấu chấm, số máy bàn `02...`, mã 12 số có mã tỉnh sai, 16 số sai Luhn,
  dãy số không có từ khoá.
- `resolve_overlaps` và `redact` đúng với span chồng lấn, span dài bằng nhau, span chạm biên.
- Giả danh hoá: không còn giá trị gốc nào trong văn bản đã thay; cùng khoá cùng token, khác khoá khác token; hai cách
  viết của cùng một số điện thoại cùng token; `restore` khôi phục được cả token nằm trong câu trả lời của LLM.
- Trên tập 150 câu sinh ngẫu nhiên có cả mẫu gây nhiễu, precision và recall của mọi loại bằng 1.

## Gợi ý

### Gợi ý 1

Viết riêng mỗi loại một regex, chạy hết, gom span lại rồi mới giải quyết chồng lấn: đừng cố viết một regex cho tất
cả. Ranh giới "không nằm trong dãy số dài hơn" là lookbehind và lookahead âm (`(?<!...)`, `(?!...)`); `\b` không đủ vì
`.` và `,` là ranh giới từ. Với từ khoá, dùng named group để lấy riêng phần số làm span.

### Gợi ý 2

Thay chuỗi theo span thì đi **từ cuối lên đầu**, để offset của các span phía trước không bị lệch sau mỗi lần thay. Khi
giải quyết chồng lấn, sắp span theo (độ dài giảm dần, thứ tự trong `KINDS`), duyệt và chỉ nhận span không đụng span
nào đã nhận. Token cần khoá bí mật vì giá trị PII có không gian nhỏ: số điện thoại chỉ khoảng $$5 \cdot 10^8$$ khả
năng, băm không khoá thì ai cũng dò ngược được trong vài phút.
