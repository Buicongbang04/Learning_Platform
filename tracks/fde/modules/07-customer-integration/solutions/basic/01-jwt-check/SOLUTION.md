# Lời giải: kiểm access token của IdP khách

Lời giải ở `jwt_check.py` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/07-customer-integration/exercises/basic/01-jwt-check -q
```

Đo 2026-11-11 trên máy của repo: 13 test ~38 s (boot `lab-open` + Keycloak ~20 s, hai lần chờ 5,5 s của quy tắc tải
lại JWKS).

## Cách làm

1. **Tách 3 phần, giải mã header/payload** để biết `alg` và `kid`. Ngoài hai giá trị đó, chưa tin gì trong token.
2. **`alg` do resource server quyết**, không do token: chỉ nhận RS*/PS*/ES*. Đây là chỗ chặn hai lỗi kinh điển:
   `alg: none` (không có chữ ký) và nhầm thuật toán `HS256` + khoá công khai (kẻ tấn công ký HMAC bằng PEM công khai mà
   ai cũng tải được từ JWKS; thư viện cũ nào "chọn thuật toán theo header" sẽ dùng PEM đó làm secret HMAC và chấp nhận).
3. **Chọn khoá theo `kid` trong JWKS**, bỏ khoá `use: enc` (Keycloak công bố cả khoá `RSA-OAEP` để mã hoá). `alg` của
   token phải hợp với khoá: trùng `alg` của JWK nếu có, không thì theo `kty`/`crv` (Entra ID không ghi `alg`). Cache
   theo URL, chia hai đường:
   - `kid` đã biết: chỉ đọc dict dưới khoá ngắn, không I/O, không bao giờ chờ.
   - `kid` lạ: tải lại JWKS **một lần** (IdP vừa xoay khoá), *single-flight* (một khoá riêng cho việc tải, lấy không
     chặn: luồng khác đang tải thì trả `unknown_key` ngay) và **ngoài** khoá cache; không quá một lần mỗi 5 s, trong
     khoảng đó trả `unknown_key` ngay. Token rác với `kid` ngẫu nhiên vì thế không biến resource server thành công cụ dội
     IdP, cũng không làm nghẽn token hợp lệ. Bản đầu của lời giải này ngủ chờ khoảng nghỉ **trong khi giữ khoá cache**:
     40 token rác đủ làm mọi request hợp lệ chờ hàng chục giây và tải JWKS 40 lần (`test_unknown_kid_flood` bắt được).
   - Bản production thêm TTL cho cache để khoá bị IdP gỡ thì cũng bị gỡ ở đây, và giới hạn theo nguồn request.
4. **Kiểm chữ ký** bằng `jwt.decode(..., algorithms=[alg])` nhưng tắt các kiểm claim của PyJWT, vì bài cần `now`
   truyền vào được (PyJWT luôn dùng đồng hồ máy). Sau chữ ký mới kiểm `iss` (so nguyên chuỗi), `aud` (chuỗi hoặc mảng),
   `exp` + 60 s, `nbf`/`iat` − 60 s.

## Vì sao từng ca quan trọng ở khách

- **Sửa payload**: không kiểm chữ ký thì `binh` tự sửa `preferred_username` thành `an`, hay thêm `groups: [legal]`.
- **Sai `aud`**: token của `an` lấy qua `admin-cli` (client khác cùng realm) vẫn ký đúng khoá, đúng issuer. Không kiểm
  `aud` thì mọi ứng dụng trong realm (portal hợp đồng, wiki…) trao token của chúng cho quillo cũng được nhận. Keycloak chỉ
  đưa `quillo` vào `aud` khi client có mapper audience (realm của khách đã có); IdP khác (Entra ID, AD FS) đặt `aud` theo
  cách riêng, đọc token thật trước khi cấu hình.
- **Issuer đúng từng ký tự**: `/` cuối, `http` vs `https`, host nội bộ vs host công khai. Đây cũng là lỗi cấu hình hay
  gặp nhất khi nối SSO: IdP đứng sau reverse proxy công bố issuer theo hostname nó được cấu hình, không theo URL bạn gõ.
- **`exp`/`iat` với lệch đồng hồ**: máy khách không có NTP (air-gapped) lệch vài phút là chuyện thường. 60 s là
  chuẩn của quillo; lệch hơn thì sửa NTP, đừng nới leeway lên 1 giờ.
- **Xoay khoá**: IT khách xoay khoá theo chính sách (hoặc sau sự cố). Cache JWKS mãi mãi ⇒ mọi người bị 401 tới khi
  restart dịch vụ; tải JWKS mỗi request ⇒ IdP chịu tải bằng số request của bạn.

## Đáp án sai thường gặp

- Tải JWKS ở mỗi lần gọi: đúng nhưng mỗi request API thành một request tới IdP (`test_jwks_not_fetched_per_call` trượt);
  cache vĩnh viễn: trượt `test_key_rotation` (đã chạy thử cả hai).
- `jwt.decode(token, key, algorithms=[header["alg"]])`: lấy danh sách thuật toán từ chính token.
- So `iss` bằng `startswith`, hoặc `rstrip("/")` cả hai phía: chấp nhận issuer của realm khác cùng host
  (`.../realms/lawfirm-test`).
- Lấy `jwks_uri` từ discovery khi chạy trên host: Keycloak công bố URL nhìn từ mạng của khách
  (`http://10.0.2.102:8080/...`), host không tới được. Ở khách thật cũng vậy (split-horizon DNS, reverse proxy): đó là
  lý do hàm nhận `jwks_url` riêng.
