---
title: "Kiểm access token của IdP khách trước khi tin nó"
level: basic
services: []
files:
  - path: starter/jwt_check.py
    note: Bản đồng nghiệp viết để "đọc nhanh claim"; bạn viết lại hàm check
  - path: tests/test_jwt_check.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - uv run pytest tracks/fde/modules/07-customer-integration/exercises/basic/01-jwt-check -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Một connector, một script báo cáo hay một extension nhỏ của quillo nhận `Authorization: Bearer <JWT>` từ người dùng
của khách. Đồng nghiệp đã viết hàm "đọc claim cho nhanh": giải mã base64, lấy `preferred_username`, xong. Ai cũng tạo
được một chuỗi như thế. Bạn viết lại hàm kiểm token **đúng như một resource server phải làm**, với token thật do
Keycloak của khách cấp: chữ ký qua JWKS, `iss`, `aud`, thời hạn, và những mánh tấn công cũ nhưng vẫn gặp.

## Đề bài

Viết `check(token, *, issuer, audience, jwks_url, now=None)` trong `starter/jwt_check.py` (Python 3.12, được dùng
`PyJWT`, `cryptography`, `requests` có sẵn trong môi trường của repo). Giữ nguyên class `TokenError` của starter.

- Token hợp lệ: trả `dict` các claim của payload.
- Token không hợp lệ: ném `TokenError` có thuộc tính `reason` là **một** trong các giá trị sau:

| `reason` | Khi nào |
| --- | --- |
| `malformed` | Không phải JWS compact đúng 3 phần, hoặc header/payload không phải base64url của một object JSON |
| `algorithm` | `alg` trong header không thuộc `RS256 RS384 RS512 PS256 PS384 PS512 ES256 ES384 ES512` |
| `unknown_key` | `kid` của header không có trong JWKS của IdP (kể cả sau khi đã tải lại JWKS) |
| `signature` | Chữ ký không khớp khoá công khai mang `kid` đó |
| `issuer` | Claim `iss` khác `issuer` (so đúng từng ký tự) |
| `audience` | Claim `aud` (chuỗi hoặc mảng) không chứa `audience` |
| `expired` | Thiếu `exp`, hoặc thời điểm kiểm muộn hơn `exp` quá 60 giây |
| `not_yet_valid` | `nbf` hoặc `iat` (nếu có) muộn hơn thời điểm kiểm quá 60 giây |

- `jwks_url` là URL của JWKS (`.../protocol/openid-connect/certs`). Quy tắc tải JWKS:
  - `kid` đã có trong JWKS đã tải: kiểm ngay, không tải lại, không bao giờ phải chờ một lần tải JWKS đang diễn ra.
  - `kid` lạ: tải lại JWKS, nhưng **không quá một lần mỗi 5 giây** cho mỗi `jwks_url` (kể cả khi nhiều luồng gọi `check`
    cùng lúc); trong khoảng đó, hoặc khi luồng khác đang tải, trả `unknown_key` ngay, không chờ.
  - Khi IdP xoay khoá (token mới mang `kid` chưa thấy), token mới phải được nhận ở lần kiểm đầu tiên sau 5 giây kể từ
    lần tải trước; token cũ còn hạn ký bằng khoá cũ (vẫn còn trong JWKS) vẫn hợp lệ.
  - Khoá trong JWKS có thể không ghi `alg` (Entra ID làm vậy): khi đó khoá RSA dùng cho `RS*`/`PS*`, khoá EC cho `ES*`
    theo đường cong.
- `now` là thời điểm kiểm (giây epoch, `float`); `None` thì lấy giờ hiện tại. Độ lệch đồng hồ cho phép: 60 giây theo
  cả hai chiều.

IdP là Keycloak của công ty luật: realm `lawfirm`, issuer `http://10.0.2.102:8080/realms/lawfirm`, client `quillo`
(token cấp cho client này có `aud` chứa `quillo`). Test boot `lab-open` (1024 MB) cùng Keycloak phía host
(`fdekit.customer_site("lab-open", memory_mb=1024, extra_services=("keycloak",))`), lấy token thật cho user `an`, `binh`,
`chi`, gọi `check` với `jwks_url` là JWKS của Keycloak qua cổng host (đi qua một proxy đếm request
của test). Cả bài ~40 s trên máy của repo. Tự boot để thử:

```python
import fdekit
with fdekit.customer_site("lab-open", memory_mb=1024, extra_services=("keycloak",)) as s:
    token = fdekit.keycloak_token(s, "an", fdekit.KEYCLOAK_PASSWORDS["an"])
    print(s.keycloak_host)
```

## Tiêu chí đạt

- `test_valid_tokens_return_claims`: token của `an`, `binh` trả claim, `preferred_username` và `sub` đúng.
- `test_jwks_not_fetched_per_call`: sau lần kiểm đầu, 5 lần kiểm tiếp (token khác nhau, cùng `kid`) không tải lại
  JWKS (test cho `jwks_url` trỏ qua một proxy nhỏ phía host đếm số request).
- `test_tampered_payload_rejected`: sửa payload (đổi tên người dùng, thêm `groups`, kéo dài `exp`) giữ chữ ký cũ ⇒
  `signature`.
- `test_wrong_audience_rejected`: token user `an` lấy qua client khác của realm (`admin-cli`) ⇒ `audience`; token của
  `quillo` kiểm với `audience="contract-portal"` ⇒ `audience`.
- `test_issuer_must_match_exactly`: cùng token, `issuer` có thêm `/` cuối, đổi `http` thành `https`, realm khác, host khác
  ⇒ `issuer`.
- `test_expiry_with_leeway`: `now = exp + 55` ⇒ hợp lệ; `exp + 65` và `exp + 86400` ⇒ `expired`.
- `test_not_yet_valid`: `now = iat - 55` ⇒ hợp lệ; `iat - 65` ⇒ `not_yet_valid`.
- `test_algorithm_tricks_rejected`: header đổi thành `alg: none` (chữ ký rỗng), hoặc `alg: HS256` ký HMAC bằng chính
  khoá công khai (PEM) của IdP ⇒ `algorithm`.
- `test_foreign_keys_rejected`: token ký bằng khoá RSA lạ với `kid` lạ ⇒ `unknown_key`; với `kid` thật của IdP ⇒
  `signature`.
- `test_malformed_rejected`: chuỗi rỗng, `abc`, `a.b`, `a.b.c`, ký tự ngoài base64url, token thật thêm phần thứ tư ⇒
  `malformed`.
- `test_jwks_without_alg`: JWKS (qua proxy của test) bỏ trường `alg` của mọi khoá ⇒ token hợp lệ vẫn được nhận.
- `test_unknown_kid_flood`: 5,5 s sau lần tải trước, 8 luồng gửi 40 token ký bằng khoá lạ với `kid` ngẫu nhiên trong lúc
  proxy JWKS trả lời chậm 1 s ⇒ cả 40 bị từ chối `unknown_key`, JWKS được tải tối đa 1 lần, và mỗi lần kiểm token `kid`
  đã biết chạy song song mất ≤ 0,5 s.
- `test_key_rotation`: test thêm khoá RSA mới ưu tiên cao hơn cho realm (như IT xoay khoá), chờ 5,5 s; token mới (kid
  mới) và token cũ đều hợp lệ.

## Gợi ý

### Gợi ý 1

Thứ tự kiểm quan trọng: có những thứ chỉ được tin **sau** khi chữ ký đã đúng. Thông tin nào trong token được phép đọc
trước khi kiểm chữ ký, và chỉ để làm gì?

### Gợi ý 2

Thư viện JWT nào cũng có tham số "danh sách thuật toán chấp nhận". Ai quyết định danh sách đó: bạn hay token?

### Gợi ý 3

JWKS có thể có nhiều khoá, kể cả khoá không dùng để ký. Cache JWKS theo `kid` và nghĩ xem lúc nào cache được phép coi
là cũ.
