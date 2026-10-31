# Lời giải: dựng chuỗi CA nội bộ

Script đầy đủ ở `make_chain.sh` cạnh tệp này.

## Cách làm

1. **Tự mang cấu hình theo.** Test chạy với `OPENSSL_CONF=/dev/null`, nên `openssl req` không có section
   `distinguished_name` nào để dựa. Script viết một tệp `req.cnf` tối thiểu và hai tệp extension (`intermediate.ext`,
   `server.ext`) bằng heredoc trong thư mục tạm. Lợi ích phụ: cert sinh ra giống nhau trên mọi máy, không phụ thuộc
   `/etc/ssl/openssl.cnf` của distro.
2. **Extension đi theo `-extfile` khi ký**, không theo CSR. CA quyết định cert mang gì; nếu CA chép extension từ CSR
   (`copy_extensions = copyall`) thì người xin cert tự cấp cho mình `CA:TRUE` được.
3. **EC P-256**: khoá nhỏ, ký nhanh, mọi client hiện đại đều hỗ trợ. Vì khoá EC không dùng để mã hoá trao đổi khoá,
   `keyEncipherment` không có nghĩa với nó; chỉ cần `digitalSignature`.
4. **An toàn khi lỗi giữa chừng**: `umask 077`, làm trong `mktemp -d` bên trong `OUTDIR`, `openssl verify` ở cuối rồi mới
   `mv` ra; `trap` dọn thư mục tạm. Kiểm `root-ca.key` ngay đầu script và exit 2: không bao giờ ghi đè CA, vì mọi cert đã
   cấp và mọi client đã tin CA cũ sẽ gãy.

## Từng extension để làm gì

| Extension | Trên CA | Trên cert server | Thiếu hoặc sai thì |
| --- | --- | --- | --- |
| `basicConstraints` | `critical, CA:TRUE` (+ `pathlen:0` ở intermediate) | `CA:FALSE` | Cert server có `CA:TRUE` ký được cert cho bất kỳ tên nào; `pathlen:0` cấm intermediate tạo thêm CA con |
| `keyUsage` | `keyCertSign, cRLSign` | `digitalSignature` | Client nghiêm ngặt từ chối cert server có `keyCertSign` hoặc thiếu `digitalSignature` |
| `extendedKeyUsage` | Thường không đặt | `serverAuth` | Thiếu thì một số client (Windows, Chrome trên nhiều nền tảng) từ chối dùng cho TLS server |
| `subjectAltName` | Không | Mọi tên và IP client dùng để gọi | Từ 2017 Chrome bỏ hẳn việc đọc CN; thiếu SAN là `hostname mismatch` |
| SKI / AKI | Có | Có | Client dựng chuỗi khó hơn khi CA có nhiều cert cùng tên (ví dụ sau khi xoay khoá CA) |

## Vì sao server phải gửi intermediate

Client chỉ có root trong kho tin cậy. Server gửi `fullchain.pem` (lá + intermediate) để client dựng được chuỗi tới root.
Gửi kèm root là thừa (client không tin root vì server gửi nó). Trình duyệt desktop đôi khi tự bù intermediate thiếu
(tải theo AIA, cache), nên "trình duyệt vào được" không chứng minh chuỗi đúng; `curl`, Python, Java, Android thì không bù.
Bài Advanced 01 là một sự cố đúng như vậy.

## Trong production

- `root-ca.key` để offline (HSM, hoặc máy không nối mạng); intermediate ký hằng ngày và có thể thu hồi, thay mà không
  phải phát lại root cho mọi client.
- Cert ngắn hạn (90 ngày, xu hướng tới 47 ngày cho cert công khai theo lịch của CA/Browser Forum) và **tự động** gia hạn:
  ACME (certbot, lego, Caddy, cert-manager trên Kubernetes). Cert càng ngắn, khoá lộ càng ít hại và quy trình gia hạn
  càng không có cơ hội "quên".
- PKI nội bộ ở quy mô thật: step-ca (Smallstep), HashiCorp Vault PKI, AWS Private CA, cert-manager với CA issuer.
  `openssl` bằng tay chỉ để học và để kiểm tra.
