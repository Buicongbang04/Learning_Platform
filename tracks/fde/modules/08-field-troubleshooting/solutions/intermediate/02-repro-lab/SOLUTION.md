# Lời giải: tái hiện lỗi của bệnh viện

## Nguyên nhân (chỉ trong solutions/)

Bệnh viện bật SSO với IdP nội bộ `https://sso.benhvien.local/...` dùng chứng chỉ do **CA nội bộ** của bệnh viện cấp, đúng
tên máy. Container `api` của quillo dùng trust store của image (certifi/Debian), không có CA đó, và
`QUILLO_OIDC_CA_FILE` để trống (`quillo/env.txt` không có dòng này). Lời gọi discovery hỏng ở bước kiểm chuỗi chứng chỉ:
`CERTIFICATE_VERIFY_FAILED … unable to get local issuer certificate`, api trả 503 cho `/oidc/login`. Token quản trị
không qua OIDC nên vẫn dùng được. Hồ sơ `hospital` có đúng "tật" này: CA nội bộ chưa được trust ở đâu cả.

## Hướng làm

1. Đọc chữ ký: `msg` `IdP lỗi`, `error` = `IdP: không lấy được <url>: ConnectError('[SSL: CERTIFICATE_VERIFY_FAILED]
   certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)')`, request `GET /oidc/login` 503.
2. Ba lớp: httpx `ConnectError` (hỏng khi kết nối), lớp TLS (`CERTIFICATE_VERIFY_FAILED`), lý do OpenSSL
   (`unable to get local issuer certificate`: server đưa chứng chỉ do một CA ký mà client không có CA đó).
3. Tái tạo đúng lớp trong cùng: một CA riêng ký chứng chỉ **lá** cho tên IdP. Các biến thể gần đúng cho chữ ký khác:
   chứng chỉ tự ký (lá = CA) cho `self-signed certificate`; không có server cho `[Errno 111] Connection refused`; tên
   không phân giải được cho `[Errno -2] Name or service not known`/`-3`; đưa CA vào `QUILLO_OIDC_CA_FILE` thì bắt tay
   TLS qua và lỗi chuyển sang tầng HTTP (với `openssl s_server -www` là `JSONDecodeError`). Riêng chứng chỉ **sai tên**
   do cùng CA lạ ký vẫn cho **đúng** chữ ký của bệnh viện: OpenSSL kiểm chuỗi trước khi kiểm tên, chuỗi đã hỏng thì không
   tới bước tên. Nghĩa là từ bundle không biết được chứng chỉ của IdP bệnh viện có đúng tên hay không: ghi điều đó vào
   ticket và kiểm ngay sau khi trust CA (lỗi tên, nếu có, sẽ lộ ra lúc đó).
4. Trên máy lab: `openssl s_server` nghe `:8443` với chứng chỉ lá (chỉ cần bắt tay TLS, lỗi xảy ra trước HTTP); quillo
   bật SSO như bệnh viện (`compose.sso.yaml`, issuer `https://sso.benhvien.local:8443/realms/benhvien`, client secret
   trong `oidc/`), tên IdP trỏ về máy lab bằng `extra_hosts: host-gateway` trong một tệp compose ghép thêm.
5. Chạy lại được: tạo khoá/chứng chỉ chỉ khi chưa có, dừng `s_server` cũ theo pidfile trước khi chạy cái mới, xoá dòng
   OIDC cũ trong `.env` trước khi ghi lại, chỉ tạo client secret khi chưa có.

Mã: `repro.sh` cạnh tệp này. Bundle `customer-bundle/` ghi thật ngày 2026-11-11 bằng `tests/capture_bundle.py`: máy
`hospital` chạy quillo (snapshot `08-field-troubleshooting-hospital`), IdP là server HTTPS nhỏ phía host với chứng chỉ của
CA lab, nối vào VM ở `10.0.2.104:443` bằng `guestfwd`.

## Kiểm thử của bài

Test so **chữ ký đầy đủ** (thông điệp + lý do sau khi bỏ URL), không chỉ `msg`, và chính test gọi `/oidc/login` sau khi
script xong, nên in dòng log giả vào stdout của container không qua được. Biến thể sai đã thử (mỗi biến thể 2 lần, đều
trượt): chứng chỉ tự ký (chữ ký `self-signed certificate`); có `QUILLO_OIDC_CA_FILE` (chữ ký `JSONDecodeError`). Biến thể
sai tên thì qua, đúng như phân tích ở bước 3.

## Phương án khác (vẫn đúng ràng buộc)

- IdP giả bằng Python `ssl` + `http.server` thay `openssl s_server`: được, `python3` có sẵn trên Ubuntu 22.04.
- Trỏ issuer vào IP của máy lab (`10.0.2.15`) với SAN là IP thay vì tên + `extra_hosts`: được nếu chứng chỉ có
  `IP:10.0.2.15` trong SAN (không có thì thành lỗi tên).
- Dùng Keycloak thật sau reverse proxy TLS: đúng hơn nhưng nặng và không cần, vì lỗi xảy ra trước HTTP.

## Sau khi tái hiện: đề xuất cho bệnh viện

Lấy CA gốc (và CA trung gian nếu có) của bệnh viện qua kênh tin cậy (không lấy từ chính kết nối đang nghi ngờ), đặt vào
`oidc/ca.pem`, đặt `QUILLO_OIDC_CA_FILE=/etc/quillo/oidc/ca.pem`, `docker compose -f compose.yaml -f compose.sso.yaml up
-d`; kiểm bằng `GET /oidc/login` trả 302 tới IdP và một lần đăng nhập thật. Không tắt kiểm chứng chỉ.
