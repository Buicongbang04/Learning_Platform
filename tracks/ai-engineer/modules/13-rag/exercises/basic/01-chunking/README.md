---
title: Chuẩn hoá NFC và chunk văn bản luật theo Khoản/Điểm
level: basic
services: []
files:
  - path: starter/chunking.py
    note: 3 hàm TODO
  - path: tests/test_chunking.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/13-rag/exercises/basic/01-chunking -q
---

## Mục tiêu

Viết bước đầu tiên của pipeline RAG: chuẩn hoá Unicode, chunk cố định có overlap, và chunk một Điều luật
theo Khoản/Điểm, mỗi chunk mang tiêu đề Điều để trích dẫn được. Đây là chunker mà capstone trợ lý pháp
luật dùng lại.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/chunking.py`, chỉ dùng thư viện chuẩn (`re`, `unicodedata`), viết:

1. `normalize(text: str) -> str`: chuẩn hoá **NFC** (mục 2 lý thuyết, "Unicode NFC"); trong mỗi dòng, gộp
   mọi chuỗi khoảng trắng (dấu cách, tab, khoảng trắng không ngắt `\u00a0`) thành một dấu cách và bỏ khoảng
   trắng ở hai đầu dòng; bỏ dòng trống; nối các dòng bằng `"\n"` (xuống dòng kiểu Windows `\r\n` cũng là
   xuống dòng). Giữ nguyên ranh giới dòng vì khoản và điểm được nhận ra theo **đầu dòng**.
2. `chunk_fixed(text: str, size: int, overlap: int) -> list[str]`: cắt theo **ký tự**, không chuẩn hoá.
   Chunk đầu bắt đầu ở ký tự 0, chunk sau bắt đầu sau chunk trước đúng $$S - O$$ ký tự, mỗi chunk dài
   $$S$$ (chunk cuối có thể ngắn hơn). Dừng ở chunk đầu tiên chạm cuối văn bản, nên số chunk của văn bản dài
   $$L > S$$ đúng bằng $$\left\lceil \frac{L - O}{S - O} \right\rceil$$. Văn bản rỗng trả `[]`. Ném `ValueError`
   khi không có $$0 \le O < S$$ (kiểm trước mọi việc khác).
3. `chunk_legal(article_text: str, max_chars: int) -> list[str]`: chunk **một Điều** luật.
   - Chuẩn hoá bằng `normalize` trước. Dòng đầu là **tiêu đề Điều** (`Điều 5. ...`); mọi dòng sau là thân.
   - **Khoản** bắt đầu ở dòng mở đầu bằng số, dấu chấm rồi khoảng trắng (`1. `, `12. `). Dòng
     `150.000 đồng ...` **không** phải khoản. Các dòng tiếp theo (kể cả các điểm) thuộc khoản đang mở.
     Các dòng trước khoản đầu tiên (nếu có) là một đơn vị riêng; Điều không có khoản nào thì cả thân là một đơn vị.
   - Đơn vị dài **không quá** `max_chars` ký tự (tính phần thân của đơn vị, các dòng nối bằng `"\n"`, không tính
     tiêu đề) thành **một** chunk: `tiêu đề + "\n" + đơn vị`.
   - Đơn vị dài hơn `max_chars` và có **điểm** thì tách theo điểm. Điểm bắt đầu ở dòng mở đầu bằng một chữ
     thường, `)` rồi khoảng trắng: `a) `, `b) `, ..., `d) `, `đ) `, `e) ` (bảng chữ cái tiếng Việt có `đ`). Mỗi
     điểm thành một chunk: `tiêu đề + "\n" + phần dẫn + "\n" + điểm`, trong đó **phần dẫn** là các dòng của
     khoản đứng trước điểm đầu tiên (thường chứa mức phạt, như `2. Phạt tiền từ ... đối với ... sau đây:`).
   - Đơn vị dài nhưng không có điểm thì giữ nguyên một chunk (không cắt giữa câu).
   - Điều chỉ có dòng tiêu đề thì trả `[tiêu đề]`.

Ví dụ với `max_chars` nhỏ, khoản 2 có ba điểm:

```text
Điều 5. Xử phạt ...                 ->  "Điều 5. Xử phạt ...\n1. Phạt tiền ... ban đêm."
1. Phạt tiền ... ban đêm.               "Điều 5. Xử phạt ...\n2. Phạt tiền ... sau đây:\na) Chở ...;"
2. Phạt tiền ... sau đây:               "Điều 5. Xử phạt ...\n2. Phạt tiền ... sau đây:\nb) Buông ...;"
a) Chở ...;                             "Điều 5. Xử phạt ...\n2. Phạt tiền ... sau đây:\nc) Vừa ..."
b) Buông ...;
c) Vừa ...
```

## Tiêu chí đạt

- `normalize` cho cùng kết quả với đầu vào NFD và NFC, gộp khoảng trắng, bỏ dòng trống, kết quả ở dạng NFC.
- Ghép `chunk_fixed` (chunk đầu, rồi mỗi chunk sau bỏ `overlap` ký tự đầu) ra đúng văn bản gốc; mọi chunk trừ
  chunk cuối dài đúng `size`; số chunk đúng công thức trên; `overlap >= size`, `overlap < 0`, `size <= 0` ném `ValueError`.
- Điều 3 khoản với `max_chars` đủ lớn cho đúng 3 chunk, chunk nào cũng bắt đầu bằng `Điều 5.`.
- Khoản dài hơn `max_chars` tách thành một chunk mỗi điểm (kể cả điểm `đ)`), mỗi chunk giữ tiêu đề và phần dẫn của
  khoản; ngưỡng là "dài hơn", không phải "dài bằng".
- Đầu vào NFD hoặc lộn xộn khoảng trắng cho kết quả giống hệt bản NFC sạch.
- Test dữ liệu thật (tự skip nếu chưa chạy `uv run python data/download_dataset.py zalo-legal`): trên 3 000 điều
  đầu của Zalo Legal, mọi chunk bắt đầu bằng tiêu đề Điều và không dòng nào của điều luật bị mất.

## Gợi ý

### Gợi ý 1

`str.split()` không đối số tách theo **mọi** loại khoảng trắng Unicode (kể cả `\u00a0`) và bỏ chuỗi rỗng;
`str.splitlines()` hiểu cả `\n` lẫn `\r\n`. Với `chunk_fixed`, điều kiện dừng là chỗ dễ sai: nếu vòng lặp chỉ
dừng khi điểm bắt đầu vượt quá độ dài văn bản, chunk cuối có thể nằm trọn trong chunk trước. Tự đếm tay với
$$L = 90, S = 50, O = 10$$ (phải ra 2 chunk, không phải 3) trước khi viết code.

### Gợi ý 2

Hai việc tách (thân Điều thành khoản, khoản thành điểm) cùng một dạng: duyệt từng dòng, dòng nào khớp mẫu thì mở
một nhóm mới, dòng không khớp thì thêm vào nhóm đang mở, hoặc vào "phần trước nhóm đầu" nếu chưa có nhóm nào.
Viết một hàm phụ nhận danh sách dòng và một regex, trả về (phần trước, danh sách nhóm), rồi gọi hai lần. Dùng
`pattern.match(line)` (khớp từ đầu chuỗi) và nhớ rằng `[a-z]` không chứa `đ`.
