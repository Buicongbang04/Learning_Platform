---
title: Đọc output dig khi sự cố - NXDOMAIN, NODATA, referral thiếu glue
level: basic
services: []
files:
  - path: starter/dig_triage.py
    note: 2 hàm có TODO
  - path: tests/test_triage.py
    note: Không sửa
  - path: tests/fixtures/cname_answer.txt
    note: Output dig thu lại, đọc để hiểu dạng dữ liệu
run:
  - uv run pytest tracks/devops/modules/04-networking-protocols/exercises/basic/01-dig-answer-triage -q
---

## Mục tiêu

Nhìn một output `dig` và nói ngay được: tên có tồn tại không, có bản ghi loại đó không, ai trả lời (authoritative hay
resolver), sửa xong thì bao lâu nữa mọi người mới thấy (TTL, kể cả TTL của câu trả lời phủ định), và delegation có thiếu
glue không. Đây là năm câu hỏi đầu tiên trong mọi sự cố "DNS hỏng".

## Đề bài

Thư mục `tests/fixtures/` có 9 output `dig` thu lại trong các sự cố của Olist Shop (bạn **không** cần cài `dig` để làm
bài; muốn thử lệnh thật thì xem mục 0 và mục 2 của lý thuyết). Viết hàm `triage(text)` trong `starter/dig_triage.py`,
nhận nguyên văn một output và trả về một `dict` đúng 10 khoá:

| Khoá | Kiểu | Quy tắc |
| --- | --- | --- |
| `qname` | `str` | Tên trong `QUESTION SECTION`, chữ thường, bỏ dấu chấm cuối |
| `qtype` | `str` | Loại bản ghi được hỏi, chữ hoa (`A`, `AAAA`, `MX`, `NS`) |
| `status` | `str` | Giá trị sau `status:` trong dòng `->>HEADER<<-` (`NOERROR`, `NXDOMAIN`, `SERVFAIL`, `REFUSED`) |
| `kind` | `str` | Xem bảng dưới |
| `authoritative` | `bool` | Dòng `;; flags:` có cờ `aa` |
| `cname_chain` | `list[str]` | Bắt đầu bằng `qname`; lặp: nếu `ANSWER SECTION` có bản ghi `CNAME` mà tên chủ (so sánh không phân biệt hoa thường, bỏ dấu chấm cuối) bằng phần tử cuối, thêm đích của CNAME (chữ thường, bỏ dấu chấm cuối). Không có CNAME thì chỉ có `qname` |
| `answers` | `list[str]` | rdata (mọi cột sau cột loại bản ghi, gộp nhiều khoảng trắng thành một dấu cách, giữ nguyên chữ) của các bản ghi trong `ANSWER SECTION` có loại bằng `qtype`, sắp xếp tăng dần theo chuỗi. Ví dụ MX: `"10 mx1.olist-shop.com.br."` |
| `ttl` | `int` hoặc `None` | `kind == "answer"`: TTL nhỏ nhất trong **mọi** bản ghi của `ANSWER SECTION` (kể cả CNAME). `kind` là `nxdomain` hoặc `nodata`: TTL phủ định = `min(TTL của bản ghi SOA trong AUTHORITY, trường MINIMUM là số cuối cùng của SOA)`; không có SOA thì `None`. Các `kind` khác: `None` |
| `missing_glue` | `list[str]` | Chỉ khi `kind == "referral"`: tên NS (chữ thường, bỏ dấu chấm cuối) nằm **trong bailiwick** (bằng hoặc là tên con của tên chủ bản ghi NS) mà `ADDITIONAL SECTION` không có bản ghi `A` hay `AAAA` nào cho tên đó; bỏ trùng, sắp xếp. Các trường hợp khác: `[]` |
| `ede` | `int` hoặc `None` | Mã Extended DNS Error trong dòng `; EDE: <số> (...)` nếu có |

`kind` xét theo thứ tự:

| Điều kiện | `kind` |
| --- | --- |
| `status` là `NXDOMAIN` / `SERVFAIL` / `REFUSED` | `nxdomain` / `servfail` / `refused` |
| `status` khác ba giá trị trên và khác `NOERROR` | `error` |
| `NOERROR` và `answers` không rỗng | `answer` |
| `NOERROR`, `answers` rỗng, `AUTHORITY` không có SOA, có NS, và không có cờ `aa` | `referral` |
| `NOERROR` và mọi trường hợp còn lại | `nodata` |

Lưu ý: `NXDOMAIN` đi kèm một CNAME trong `ANSWER` vẫn là `nxdomain` (mã trả lời nói về **tên cuối chuỗi**, RFC 6604):
tên bạn hỏi tồn tại, nhưng nó trỏ tới một tên không tồn tại.

`split_sections` đã viết sẵn, dùng hay không tuỳ bạn. Không dùng mạng, không gọi `dig`: test chỉ đưa chuỗi vào hàm.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/04-networking-protocols/exercises/basic/01-dig-answer-triage -q` pass.
- Với mỗi fixture, nói được bằng một câu cho người trực ca: chuyện gì xảy ra và bước tiếp theo. Ví dụ
  `cname_to_nxdomain.txt`: "`promo` còn CNAME tới trang chiến dịch đã xoá; xoá CNAME hoặc trỏ lại, resolver còn nhớ câu
  trả lời phủ định tối đa 10 phút".
- Giải thích được vì sao `servfail_dnssec.txt` không phải lỗi của resolver `1.1.1.1` và ai phải sửa.

## Gợi ý

### Gợi ý 1

Mỗi dòng bản ghi có dạng `name ttl class type rdata...`, tách bằng `line.split()` là đủ: phần tử 0 là tên, 1 là TTL,
3 là loại, từ 4 trở đi là rdata. Dòng câu hỏi bắt đầu bằng `;` và không có TTL: `;shop.olist-shop.com.br. IN A`.

### Gợi ý 2

NODATA và referral đều là `NOERROR` không có câu trả lời. Khác biệt: NODATA mang SOA của zone (để resolver biết nhớ câu
trả lời phủ định bao lâu), còn referral mang NS của zone con và thường không có cờ `aa` vì server cha không có thẩm
quyền với zone con. Glue chỉ cần cho NS nằm **bên trong** zone được uỷ quyền: muốn hỏi `ns2.olist-shop.com.br` thì phải
biết IP của nó trước khi hỏi được chính zone đó.
