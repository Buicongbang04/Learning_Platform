---
title: Kết luận SPF, DKIM, DMARC cho từng thư - phân tích offline
level: intermediate
services: []
files:
  - path: starter/email_auth.py
    note: 4 hàm có TODO; load_records, load_suffixes đã viết sẵn
  - path: tests/test_email_auth.py
    note: Không sửa
  - path: tests/fixtures/zones/olist-shop.com.br.zone
    note: Bản ghi DNS của Olist Shop (zone file), đọc trước khi làm
  - path: tests/fixtures/messages/03-forwarded-alumni.eml
    note: Một thư mẫu, 12 thư còn lại cùng thư mục
run:
  - uv run pytest tracks/devops/modules/04-networking-protocols/exercises/intermediate/01-email-auth-verdict -q
---

## Mục tiêu

Tự đi lại đúng con đường mà máy chủ nhận thư đi khi quyết định nhận, đưa vào spam hay từ chối một thư: SPF trên envelope
sender, DKIM qua `Authentication-Results`, alignment với tên miền trong `From`, chính sách DMARC kể cả `sp` và `pct`.
Sau bài này bạn đọc được header của một thư bị vào spam và chỉ ra chính xác mắt xích nào gãy.

## Đề bài

Bạn là người vận hành hộp thư của `cliente-mail.example`. MX của bạn là `mx.cliente-mail.example`. `tests/fixtures/` có:

- `zones/*.zone`: zone file (định dạng master file chuẩn) của 6 tên miền. `load_records(zone_dir)` đã viết sẵn bằng
  dnspython, trả `{(tên, loại): [rdata, ...]}`; tên chữ thường không dấu chấm cuối, TXT đã ghép các chuỗi con. Đây là
  "DNS" duy nhất của bài: không tra DNS thật.
- `public_suffixes.txt`: danh sách hậu tố công khai thu gọn (bản thật là Public Suffix List). `load_suffixes` đọc nó.
- `messages/*.eml`: 13 thư thật-dạng. Phần header là thứ cần đọc.

Viết bốn hàm trong `starter/email_auth.py`.

### `org_domain(domain, suffixes)`

Chuẩn hoá `domain` (chữ thường, bỏ dấu chấm cuối). Tìm hậu tố dài nhất (nhiều nhãn nhất) trong `suffixes` mà `domain`
bằng nó hoặc kết thúc bằng `"." + hậu tố`. Không khớp hậu tố nào thì coi **nhãn cuối** là hậu tố (quy tắc `*` của PSL).
`domain` bằng đúng hậu tố thì trả chính nó; ngược lại trả hậu tố cộng **một** nhãn bên trái. Ví dụ
`news.olist-shop.com.br` → `olist-shop.com.br` (vì `com.br` là hậu tố), `deep.mail.unlisted-tld` → `mail.unlisted-tld`.

### `aligned(a, b, mode, suffixes)`

`mode == "s"` (strict): hai tên (đã chuẩn hoá) bằng nhau. `mode == "r"` (relaxed): `org_domain(a) == org_domain(b)`.

### `spf_check(ip, domain, records)`

Trả một trong `pass`, `fail`, `softfail`, `neutral`, `none`, `permerror` (tập con của RFC 7208):

| Bước | Quy tắc |
| --- | --- |
| Chọn bản ghi | Các TXT của `domain` bằng đúng `v=spf1` hoặc bắt đầu bằng `v=spf1 ` (so sánh không phân biệt hoa thường; `v=spf10` không tính). Không có → `none`. Hơn một → `permerror` |
| Duyệt | Các term sau `v=spf1`, tách bằng khoảng trắng, từ trái sang phải. Term đầu tiên **khớp** quyết định kết quả theo qualifier: `+` (mặc định khi không ghi) → `pass`, `-` → `fail`, `~` → `softfail`, `?` → `neutral` |
| `all` | Luôn khớp |
| `ip4:<địa chỉ>[/<prefix>]`, `ip6:<địa chỉ>[/<prefix>]` | Khớp khi `ip` nằm trong mạng; không ghi prefix là đúng một địa chỉ. IPv4 không bao giờ khớp `ip6` và ngược lại |
| `a[:<tên>][/<prefix>]` | Lấy bản ghi `A` và `AAAA` của `<tên>` (mặc định `domain`); khớp khi `ip` bằng một địa chỉ, hoặc với IPv4 có `/<prefix>` thì khi `ip` nằm trong mạng `<địa chỉ>/<prefix>` |
| `mx[:<tên>][/<prefix>]` | Lấy các bản ghi `MX` của `<tên>` (mặc định `domain`), với mỗi exchange (từ cuối rdata, bỏ dấu chấm cuối) xét như `a:<exchange>[/<prefix>]` |
| `include:<tên>` | Đánh giá SPF của `<tên>` (đệ quy). Kết quả `pass` → khớp. `fail`, `softfail`, `neutral` → **không khớp**, đi tiếp term sau. `none` (tên đó không có SPF) → `permerror` cho cả lần kiểm. `permerror` → `permerror` |
| `redirect=<tên>` | Chỉ dùng khi **không** term nào khớp: kết quả là SPF của `<tên>`; `<tên>` không có SPF → `permerror`. Có `all` thì `all` luôn khớp trước, `redirect` bị bỏ qua |
| Modifier khác (`exp=...`, có `=` trước dấu `:` đầu tiên) | Bỏ qua |
| Cơ chế khác | `permerror` (bài không có `ptr`, `exists`) |
| Giới hạn tra DNS | Mỗi `include`, `a`, `mx`, `redirect` **được thực sự đánh giá** tính một lượt, cộng dồn qua mọi tầng include. Lượt thứ 11 → `permerror`. Term nằm sau term đã khớp không được đánh giá nên không tính |
| Hết term, không khớp, không redirect | `neutral` |

### `evaluate(raw, records, suffixes)`

`raw` là nguyên văn một tệp `.eml`. Trả `dict` đúng 9 khoá:

| Khoá | Quy tắc |
| --- | --- |
| `from_domain` | Phần sau `@` của địa chỉ trong header `From` (dùng `email.utils.getaddresses`), chuẩn hoá. Tên hiển thị không quan trọng |
| `spf_domain` | Lấy địa chỉ trong header `Return-Path`. Có `@` → phần sau `@`. Rỗng (`<>`, thư bounce) → **HELO**: từ ngay sau `from` trong header `Received` **trên cùng**. Chuẩn hoá |
| `spf` | `spf_check(ip, spf_domain, records)`, với `ip` là chuỗi trong cặp `[...]` đầu tiên của header `Received` **trên cùng** (do chính MX của bạn ghi; các `Received` bên dưới do máy khác ghi, có thể là giả). Không dùng `spf=` trong `Authentication-Results` |
| `spf_aligned` | `spf == "pass"` **và** `aligned(spf_domain, from_domain, aspf, ...)` |
| `dkim_aligned` | Chỉ đọc header `Authentication-Results` **đầu tiên** (trên cùng), và chỉ khi authserv-id (phần trước dấu `;` đầu tiên, bỏ khoảng trắng) đúng bằng `mx.cliente-mail.example`; các header `Authentication-Results` khác bị bỏ qua hoàn toàn. Trong header đó, mỗi phần tách bằng `;` có từ đầu là `dkim=pass` mang một tên miền ở `header.d=`. `True` khi có ít nhất một tên miền như vậy `aligned(d, from_domain, adkim, ...)`. Header `DKIM-Signature` **không** phải bằng chứng: chữ ký có thể sai |
| `dmarc` | Không tìm được bản ghi DMARC → `none`. Có: `pass` nếu `spf_aligned` hoặc `dkim_aligned`, ngược lại `fail` |
| `policy` | Không có bản ghi → `None`. Bản ghi tìm ở chính `from_domain` → tag `p`. Bản ghi tìm ở organizational domain → tag `sp` nếu có, không thì `p`. Chữ thường |
| `disposition` | `dmarc` là `pass` hoặc `none` → `deliver`. `fail` → theo `policy`: `none` → `deliver`, `quarantine` → `quarantine`, `reject` → `reject` |
| `fallback` | Cách xử lý thư **không** rơi vào mẫu `pct`. `dmarc == "fail"` và `pct < 100` → hạ một bậc: `reject` → `quarantine`, `quarantine` → `deliver`, `none` → `deliver`. Mọi trường hợp khác bằng `disposition` |

Tìm bản ghi DMARC: TXT tại `_dmarc.<from_domain>` bắt đầu bằng `v=DMARC1` (không phân biệt hoa thường). Không có thì,
nếu `org_domain(from_domain)` khác `from_domain`, tìm tại `_dmarc.<organizational domain>`. Ở một tên mà có hơn một bản
ghi `v=DMARC1` thì coi như không có. Tag tách bằng `;`, mỗi tag `tên=giá trị`, bỏ khoảng trắng hai bên. Mặc định: `adkim`
và `aspf` là `r`, `pct` là `100`. Khi không có bản ghi, alignment vẫn tính với `r`.

Test gọi bốn hàm trực tiếp (trong tiến trình pytest, không chạy tiến trình con, không ghi tệp): 8 ca `org_domain`, 5 ca
`aligned`, 26 ca `spf_check` dựng sẵn trong test, 2 ca giới hạn tra DNS, và 13 thư với đủ 9 khoá. Một test nữa chứng minh
bộ thư bắt được hai lối tắt hay gặp (lấy hai nhãn cuối làm organizational domain, tin mọi `Authentication-Results`).

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/04-networking-protocols/exercises/intermediate/01-email-auth-verdict -q` pass.
- Giải thích được bằng lời cho từng thư vì sao kết luận như vậy, đặc biệt: vì sao thư 03 (forward) vẫn `pass` còn thư
  04 (mailing list) bị `reject`; vì sao thư 07 giả mạo mà vẫn `pass`; vì sao thư 10 bị từ chối dù cả SPF lẫn DKIM đều
  `pass`.
- Đề xuất được hai thay đổi cấu hình phía Olist Shop để thư 04 và thư 09 không bị chặn nữa.

## Gợi ý

### Gợi ý 1

Viết `spf_check` thành hàm đệ quy nội bộ nhận thêm một bộ đếm dùng chung (ví dụ list một phần tử `[0]`) và ném một
exception riêng khi gặp permerror; hàm ngoài cùng bắt exception đó và trả `"permerror"`. Module `ipaddress` lo hết phần
CIDR: `ipaddress.ip_address(ip) in ipaddress.ip_network("203.0.113.0/28")`.

### Gợi ý 2

`email.message_from_string(raw).get_all("Received")` trả các header theo thứ tự từ trên xuống, nên phần tử `[0]` là header
MX của bạn vừa thêm. Header gập nhiều dòng: `" ".join(value.split())` gộp lại thành một dòng. Trong
`Authentication-Results`, tách theo `;` rồi xét từng phần: `dkim=pass header.d=olist-shop.com.br header.s=s2026`.
