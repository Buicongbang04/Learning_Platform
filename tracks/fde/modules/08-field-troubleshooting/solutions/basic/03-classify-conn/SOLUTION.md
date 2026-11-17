# Lời giải: phân loại output kết nối

## Hướng làm

Một kết nối dừng ở **bước đầu tiên** hỏng, và output chứa dấu vết của mọi bước đã qua. Vì vậy kiểm theo thứ tự ngược với
đường đi (bước muộn nhất trước), dừng ở loại đầu tiên khớp:

1. `proxy-auth`: `407`, `Proxy Authentication Required`, `Proxy-Authenticate:`. Kiểm trước TLS vì CONNECT bị 407 thì
   không có bước TLS nào; mẫu HTTP thường (`curl http://…` qua proxy) thoát `0` mà vẫn là lỗi này.
2. `tls-hostname`: `Hostname mismatch`, `no alternative certificate subject name`, `does not match target host name`.
   Phải trước `tls-ca` vì OpenSSL in cả `Verification error` cho lỗi tên.
3. `tls-ca`: `unable to get local issuer certificate`, `self-signed certificate`, `unable to verify the first
   certificate`, `certificate verify failed`, `SSL certificate problem`, `Verification error`. `openssl s_client` thoát
   `0` dù verify lỗi.
4. `dns`: `Could not resolve host/proxy`, `Name or service not known`, `Temporary failure in name resolution`; và
   `getent` không in gì (không phân giải được, exit 2 mà khách không gửi).
5. `route`: `No route to host`, `Network is unreachable`.
6. `refused`: `Connection refused`, `errno=111`.
7. `timeout`: `timed out`.
8. Còn lại `ok` (có `HTTP/… 200`, `Verification: OK`, `getent` có địa chỉ).

Bẫy trong dữ liệu thật: `bank-openssl-dns` in `connect:errno=11` (EAGAIN, không phải `ECONNREFUSED` 111 hay
`EHOSTUNREACH` 113) sau dòng `Name or service not known`; mã curl `7` dùng chung cho refused và route; curl qua proxy
in `Trying 10.0.2.100:3128` cho cả lỗi ở phía đích.

Mã: `classify_conn.py` cạnh tệp này.

## Nguồn dữ liệu

27 mẫu ghi thật ngày 2026-11-11 bằng `tests/capture_samples.py` (đọc docstring): `customer_site("hospital")` với
mitmproxy TLS inspection, CA chưa trust; `vm("hospital")` với một mitmproxy `--proxyauth` đặt ở địa chỉ proxy
(`guestfwd`); `vm("bank")` không mạng. Server TLS nội bộ là `openssl s_server` trong VM với CA tự tạo; đích "treo" là
`10.255.255.1` qua proxy. Nhãn viết tay sau khi đọc output.

## Phương án khác

- Dùng mã thoát/`errno` làm tín hiệu chính: khách không gửi mã thoát và errno dễ lừa (xem trên), nên chỉ là tín hiệu phụ.
- Học máy trên nhãn: 27 mẫu không đủ và không giải thích được; quy tắc theo bước của kết nối là thứ bạn cần nói được
  với khách.
