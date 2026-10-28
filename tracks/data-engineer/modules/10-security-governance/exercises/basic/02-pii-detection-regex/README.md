---
title: Phát hiện PII bằng regex và checksum
level: basic
services: []
files:
  - path: starter/pii.py
    note: 6 TODO
  - path: tests/test_pii.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/basic/02-pii-detection-regex -q
---

## Mục tiêu

Viết một PII scanner nhỏ: tìm email, số điện thoại Việt Nam, CPF Brazil và số thẻ trong văn bản, dùng
checksum (CPF, Luhn) để giảm false positive, rồi quét một DataFrame để gợi ý tag PII cho từng cột.

## Đề bài

Hoàn thiện `starter/pii.py`:

1. `luhn_ok(number)`: lấy các chữ số trong chuỗi; đúng khi có 13–19 chữ số và qua thuật toán Luhn.
2. `cpf_ok(cpf)`: lấy các chữ số; đúng khi có đúng 11 chữ số, không phải 11 số giống nhau
   (`111.111.111-11` là sai), và 2 chữ số cuối khớp checksum CPF:
   - d1: nhân 9 số đầu lần lượt với 10, 9, …, 2, lấy tổng `s`; `r = (s * 10) % 11`, nếu `r == 10` thì `r = 0`.
   - d2: nhân 10 số đầu với 11, 10, …, 2, làm tương tự.
3. `detect(text)`: trả list dict `{"type", "value", "start", "end"}` sắp theo `start`. Các loại:
   - `email`: dạng `local@domain.tld` thông thường.
   - `card`: 13–19 chữ số, có thể ngăn bởi dấu cách hoặc `-`, **phải** qua `luhn_ok`.
   - `cpf`: `ddd.ddd.ddd-dd` hoặc 11 chữ số liền, **phải** qua `cpf_ok`.
   - `phone`: số di động Việt Nam `0` hoặc `+84` rồi một trong `3,5,7,8,9` và thêm 8 chữ số; giữa các
     chữ số sau đầu số cho phép dấu cách hoặc dấu chấm (`0912 345 678`, `+84 912.345.678`).
   Các match không được chồng lên nhau. Thứ tự ưu tiên khi chồng: `email` > `card` > `cpf` > `phone`.
   Không ghép nhầm một phần của dãy số dài hơn (dùng `(?<!\d)` và `(?!\d)`).
4. `redact(text)`: thay mỗi match bằng `[EMAIL]`, `[CARD]`, `[CPF]`, `[PHONE]`.
5. `scan_dataframe(df, sample_size=1000, threshold=0.3)`: với mỗi cột kiểu chuỗi, lấy tối đa
   `sample_size` giá trị không null (dùng `.head()` để kết quả ổn định), tính tỉ lệ giá trị có chứa từng
   loại PII. Trả `{cột: set(loại)}` gồm các loại có tỉ lệ `>= threshold`; cột không có loại nào thì
   không xuất hiện trong kết quả.

## Tiêu chí đạt

- CPF và số thẻ sai checksum không bị báo.
- Email chứa chữ số không bị nhận nhầm thành phone/CPF.
- `redact` không để lại PII nào mà `detect` tìm thấy.
- `scan_dataframe` tag đúng cột `email`, `phone`, `cpf` và tôn trọng `threshold` với cột free text.
- Test pass.

## Gợi ý

### Gợi ý 1

Cách đơn giản để xử lý chồng lấn: chạy pattern theo thứ tự ưu tiên, giữ một list các khoảng đã chiếm,
bỏ match mới nếu `start < e and s < end` với khoảng đã có.

### Gợi ý 2

Luhn: đảo ngược dãy chữ số, nhân đôi các vị trí lẻ (chỉ số 1, 3, 5…), nếu > 9 thì trừ 9, tổng chia hết
cho 10 là hợp lệ. Regex thẻ: `(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)`.
