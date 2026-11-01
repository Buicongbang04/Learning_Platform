---
title: Dựng chuỗi CA nội bộ - root, intermediate, cert server có SAN
level: intermediate
services: []
files:
  - path: starter/make_chain.sh
    note: 3 TODO
  - path: tests/test_chain.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/04-networking-protocols/exercises/intermediate/03-tls-ca-chain -q
---

## Mục tiêu

Tự dựng một PKI nhỏ đúng như CA thật làm: root CA giữ offline, intermediate CA ký cert hằng ngày, cert server có SAN và
key usage đúng, server gửi đúng chuỗi. Sau bài này `unable to get local issuer certificate`, `hostname mismatch` và
`certificate has expired` không còn là câu thần chú: bạn biết từng lỗi đến từ trường nào của cert.

## Đề bài

Môi trường lab của Olist Shop cần HTTPS cho `shop.olist.test` và `api.olist.test` mà không phụ thuộc CA công khai. Viết
`starter/make_chain.sh OUTDIR` (Bash + `openssl`) tạo đúng 7 tệp trong `OUTDIR` (tạo thư mục nếu chưa có):

| Tệp | Yêu cầu |
| --- | --- |
| `root-ca.key`, `root-ca.crt` | Tự ký (issuer = subject). `basicConstraints` **critical** `CA:TRUE`. `keyUsage` **critical** có `keyCertSign` và `cRLSign`. Còn hiệu lực ít nhất 1825 ngày tính từ lúc chạy |
| `intermediate-ca.key`, `intermediate-ca.crt` | Do root ký. `basicConstraints` **critical** `CA:TRUE, pathlen:0`. `keyUsage` như root. Còn hiệu lực ít nhất 365 ngày, không quá hạn root |
| `server.key`, `server.crt` | Do **intermediate** ký (không phải root). `basicConstraints` `CA:FALSE`. `keyUsage` **critical** có `digitalSignature`, không có `keyCertSign` hay `cRLSign`; `keyEncipherment` chỉ được có khi khoá là RSA. `extendedKeyUsage` có `serverAuth`. `subjectAltName` **đúng** ba mục `DNS:shop.olist.test`, `DNS:api.olist.test`, `IP:127.0.0.1`, không thừa không thiếu. Thời hạn còn lại từ 30 tới 397 ngày, không quá hạn intermediate |
| `fullchain.pem` | Đúng 2 cert theo thứ tự: `server.crt` rồi `intermediate-ca.crt`. Không kèm root |

Áp cho mọi cert và khoá:

- Khoá RSA từ 2048 bit, hoặc EC P-256 / P-384. Mỗi `.key` khớp với `.crt` cùng tên.
- Ba tệp `.key` có quyền không cho group và others đọc (`600`).
- Cert đã có hiệu lực lúc chạy (cho phép lệch đồng hồ 5 phút); test đo mọi thời hạn so với giờ UTC lúc chạy test.

Mã thoát: `0` khi tạo xong. Nếu `OUTDIR/root-ca.key` đã tồn tại: exit `2` và **không** sửa, xoá hay tạo tệp nào trong
`OUTDIR` (không bao giờ ghi đè một CA). Script phải sạch `shellcheck -S style` và không còn chữ `TODO`.

**Test**: script chạy trong sandbox bubblewrap (thiếu `bwrap` thì skip) với môi trường dựng lại từ đầu:
`OPENSSL_CONF=/dev/null` (không có cấu hình mặc định nào của distro, mọi extension phải do bạn khai báo), `HOME` và
`SSL_CERT_FILE`/`SSL_CERT_DIR` trỏ vào thư mục tạm. Thiếu `openssl` hoặc OpenSSL cũ hơn 1.1.1 thì skip. Sau đó test:

1. Đọc 7 tệp bằng thư viện `cryptography` và kiểm từng dòng của bảng trên.
2. `openssl verify -no-CApath -CAfile root-ca.crt -untrusted intermediate-ca.crt` với `-verify_hostname shop.olist.test`
   và `-verify_ip 127.0.0.1` phải OK; bỏ `-untrusted` thì phải lỗi; `-verify_hostname admin.olist.test` phải báo
   `hostname mismatch`. Lệnh `openssl` của test cũng chạy với `OPENSSL_CONF=/dev/null` và không đọc kho CA của hệ thống.
3. Dựng một TLS server Python trên `127.0.0.1` cổng ngẫu nhiên với `fullchain.pem` + `server.key`; client chỉ tin
   `root-ca.crt`, gửi SNI `shop.olist.test`, `api.olist.test`, `127.0.0.1` phải bắt tay được; `admin.olist.test` phải
   bị từ chối. Server chỉ gửi `server.crt` (thiếu intermediate) thì client phải bị từ chối.
4. Chạy lại script trên một bản sao thư mục đã có CA: exit 2, mọi tệp giữ nguyên.

Hai test nữa tự sinh các bộ cert lỗi (cert server hết hạn, SAN sai, cert server là CA, `fullchain.pem` thiếu
intermediate) và đòi phép kiểm ở bước 1 bắt được từng lỗi, `openssl verify` báo `expired`, TLS báo `expired` và
`mismatch`: đó là các lỗi bạn sẽ gặp lại ở bài Advanced 01.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/04-networking-protocols/exercises/intermediate/03-tls-ca-chain -q` pass, gồm
  `shellcheck` sạch.
- Chạy `openssl x509 -in <OUTDIR>/server.crt -noout -text` và chỉ ra từng extension trong bảng.
- Giải thích được vì sao trình duyệt đôi khi vẫn vào được site có chuỗi thiếu intermediate, trong khi `curl`, Java hay
  Python thì không (mục 4 của lý thuyết).
- Nói được trong production bạn giữ `root-ca.key` ở đâu, và vì sao cert server chỉ nên sống 90 ngày.

## Gợi ý

### Gợi ý 1

Ba lệnh làm gần hết việc: `openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out x.key`;
`openssl req -new -x509` (root) hoặc `openssl req -new` (CSR) với `-subj` và một tệp `-config` tối thiểu
(`[req]` có `distinguished_name = dn` và `prompt = no`, cộng một section `[dn]`), vì `OPENSSL_CONF=/dev/null` làm
`req` không có cấu hình nào để dựa; `openssl x509 -req -CA ... -CAkey ... -extfile ext.cnf` để ký. Extension của cert
được ký nằm trong `-extfile`, không phải trong CSR.

### Gợi ý 2

Làm trong một thư mục tạm bên trong `OUTDIR` (`mktemp -d "$out/.work.XXXXXX"` + `trap ... EXIT`), `umask 077` trước khi
sinh khoá, kiểm bằng `openssl verify` ở cuối rồi mới `mv` tệp ra chỗ chính thức: lỗi giữa chừng không để lại một
`root-ca.key` dở dang làm lần chạy sau tưởng CA đã có. Ghi rõ `subjectKeyIdentifier = hash` và
`authorityKeyIdentifier = keyid:always` trong tệp extension: mặc định của từng bản OpenSSL khác nhau, ghi rõ thì cert
giống nhau trên 1.1.1 và 3.x, và client dựng chuỗi nhanh hơn khi CA có nhiều cert cùng tên.
