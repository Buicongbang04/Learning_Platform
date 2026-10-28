---
title: Masking, pseudonymization và tokenization dữ liệu khách hàng
level: basic
services: []
files:
  - path: starter/protect.py
    note: 5 TODO
  - path: tests/test_protect.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/basic/01-masking-tokenization -q
---

## Mục tiêu

Tự viết các kỹ thuật che PII cơ bản: partial masking, pseudonymization bằng HMAC, tokenization có vault
mã hoá bằng Fernet, và áp policy masking lên cả một DataFrame khách hàng Olist.

## Đề bài

Hoàn thiện `starter/protect.py`:

1. `mask_email(email)`: giữ ký tự đầu của phần trước `@` và toàn bộ domain:
   `"maria.silva@gmail.com"` → `"m***@gmail.com"`. Chuỗi không có `@` (hoặc phần trước `@` rỗng) trả
   `"***"`. `None` trả `None`.
2. `mask_phone(phone)`: bỏ mọi ký tự không phải chữ số, giữ 4 số cuối, thay các số còn lại bằng `*`:
   `"+55 (11) 98765-4321"` → `"*********4321"`. Ít hơn hoặc bằng 4 chữ số thì thay tất cả bằng `*`.
   `None` trả `None`.
3. `pseudonymize(value, key, length=16)`: HMAC-SHA256 của `value` (UTF-8) với `key`, trả `length` ký tự
   hex đầu. Cùng value + key → cùng kết quả; khác key → khác kết quả.
4. Lớp `Tokenizer(fernet_key, hmac_key)`:
   - `tokenize(value)` trả token dạng `"tok_" + 24 ký tự hex` (dùng HMAC của value với `hmac_key`),
     cùng value luôn ra cùng token, và lưu vào `self.vault` (dict token → **ciphertext Fernet** dạng `bytes`).
     Vault **không được** chứa plaintext.
   - `detokenize(token)` giải mã và trả giá trị gốc; token không có trong vault thì raise `KeyError`.
5. `mask_dataframe(df, policy, key)`: trả DataFrame **mới** (không sửa `df`), với mỗi cột trong `policy`
   áp action: `"email"` → `mask_email`, `"phone"` → `mask_phone`, `"pseudonym"` → `pseudonymize(str(v), key)`,
   `"redact"` → mọi giá trị thành `"REDACTED"`, `"drop"` → bỏ cột.
   Với `email`, `phone`, `pseudonym`, giá trị rỗng (`None` hoặc NaN) giữ thành `None`.
   Action khác thì raise `ValueError`. Cột không có trong policy giữ nguyên.

## Tiêu chí đạt

- `mask_email`, `mask_phone` đúng các ví dụ và trường hợp biên.
- `pseudonymize` deterministic, phụ thuộc key, đúng độ dài.
- Token ổn định, vault chỉ chứa ciphertext, `detokenize` trả đúng giá trị gốc.
- `mask_dataframe` không thay đổi DataFrame đầu vào và báo lỗi với action lạ.
- `uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/basic/01-masking-tokenization -q` pass.

## Gợi ý

### Gợi ý 1

`hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()`. Fernet nhận key do
`Fernet.generate_key()` sinh; `Fernet(key).encrypt(b"...")` trả `bytes`.

### Gợi ý 2

Trong `mask_dataframe`, bắt đầu bằng `out = df.copy()`, rồi `out[col] = out[col].map(func)`. Với
pseudonym, kiểm tra `pd.isna(v)` trước khi gọi hàm.
