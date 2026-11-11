# Lời giải: SSO của công ty luật, đăng nhập được mà không thấy gì

Lời giải là `sso.env` và `idp-request.json` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/07-customer-integration/exercises/intermediate/01-sso-acl -q
```

Đo 2026-11-11 trên máy của repo: ~36–40 s (boot snapshot + Keycloak ~20 s, nạp 6 tài liệu ~5 s, bật SSO ~8 s, kiểm và
hai câu `/api/ask` ~5 s).

## Hai nguyên nhân (chỉ có ở đây)

1. **Token không có claim nhóm.** Keycloak không đưa nhóm vào token khi client không có mapper *Group Membership* (cấu
   hình mặc định của Keycloak, và realm của khách chỉ có mapper audience). Quillo đọc nhóm từ claim
   `QUILLO_OIDC_GROUPS_CLAIM` (mặc định `groups`); không có claim ⇒ người dùng không thuộc nhóm nào ⇒ ACL không khớp gì.
   Đăng nhập vẫn thành công vì chữ ký, `iss`, `aud`, `exp` đều đúng.
2. **ACL ghi tên thư mục không tồn tại trong quillo.** Đồng nghiệp chép ví dụ `legal:legal/,finance:finance/` của README
   sản phẩm, nhưng tài liệu của khách nằm dưới `Pháp chế/`, `Tài chính/`. Quillo lưu đường dẫn đã làm sạch từng phần
   (ký tự ngoài `A-Za-z0-9._ -` thành `_`): `Ph_p ch_/H_p _ng/NDA Minh Ph_t.txt`, `T_i ch_nh/Ho_ _n qu_ 3.txt`. ACL so
   tiền tố trên chuỗi **đã lưu**. Ghi `legal:Pháp chế/` thì quillo không khởi động (ACL chỉ nhận ký tự ASCII như trên).

Mỗi nguyên nhân che nguyên nhân kia: chỉ thêm mapper thì vẫn 0 tài liệu (ACL sai tên), chỉ sửa ACL thì vẫn 0 (không có
nhóm). Đây là lý do ticket kiểu "không thấy gì" cần chẩn đoán theo từng nửa.

## Đường chẩn đoán

```bash
PYTHONPATH=. uv run python tracks/fde/modules/07-customer-integration/exercises/intermediate/01-sso-acl/tests/test_sso_acl.py
```

1. **Nửa "người gọi là ai"**: lấy token của `an` (password grant của client `quillo` qua cổng host Keycloak, như
   `fdekit.keycloak_token`) rồi `GET /api/me` ⇒ `{"user": "an", "groups": [], "admin": false}`. Quillo nhận token (không
   401) nhưng `groups` rỗng. Giải mã payload của token (base64url, hoặc `jwt_check.py` ở bài basic 01): có `sub`,
   `preferred_username`, `email`, `aud: quillo`, **không** có `groups`. Đó là việc của IdP, không sửa được trong quillo.
2. **Nửa "tài liệu nào khớp"**: `GET /api/documents` bằng token quản trị ⇒ `filename` là `Ph_p ch_/...`,
   `T_i ch_nh/...`, `Ban gi_m _c/...`. So với `QUILLO_ACL=legal:legal/,...` ⇒ không tiền tố nào khớp.
3. **Thử trong lab trước khi gửi IT**: thêm mapper bằng admin REST API (lab có quyền admin; khách thật thì không), lấy
   token mới, `/api/me` ⇒ `"groups": ["legal"]`. Viết lại đúng mapper đó vào `idp-request.json`, xoá khỏi Keycloak lab,
   chạy test.

## `idp-request.json`

Một `add-protocol-mapper` loại `oidc-group-membership-mapper`, claim `groups`, vào access token (bắt buộc: API của quillo
đọc access token), ID token và userinfo (để UI và công cụ chẩn đoán thấy cùng thông tin). `full.path` để `false` cho tên
nhóm gọn (`legal`); `true` (mặc định của Keycloak, tên `/legal`) cũng qua vì quillo bỏ `/` đầu/cuối, nhưng nhóm lồng
nhau (`/legal/hop-dong`) khi đó thành `legal/hop-dong`, không dùng được trong `QUILLO_ACL`. Lý do (`why`) viết cho IT:
cần gì, vì sao, phạm vi ảnh hưởng (chỉ client `quillo`, chỉ nhóm của chính người đăng nhập).

## Phương án khác

| Phương án | Qua test? | Ghi chú |
| --- | --- | --- |
| Mapper `full.path: true` | Qua | Đúng với realm phẳng của khách; kém hơn khi khách có nhóm lồng nhau |
| Gán client scope có sẵn `microprofile-jwt` (`add-default-client-scope`) | **Không** | Scope này có claim `groups` nhưng lấy từ **realm role**, không phải group; user của khách không có realm role riêng nên `/api/me` vẫn `"groups": []` (đã chạy thử) |
| Mapper `oidc-hardcoded-claim-mapper` với `groups: ["legal","finance"]` | **Không** | Ai cũng thuộc mọi nhóm: `binh` thấy Pháp chế (đã chạy thử: an thấy 5 tài liệu) |
| Mapper chỉ bật `id.token.claim` | **Không** | API nhận access token: `/api/me` vẫn `"groups": []`, 0 tài liệu (đã chạy thử); UI đăng nhập qua code flow thì đọc nhóm từ ID token nên trông như "chạy" |
| Đổi `QUILLO_OIDC_GROUPS_CLAIM` sang claim khác có sẵn (vd. `email`) | **Không** | Không có claim nào sẵn trong token mang nhóm |
| ACL `legal:Pháp chế/` | **Không** | api không khởi động, log `QUILLO_ACL: 'legal:Pháp chế/' không đúng dạng nhóm:thư_mục` (đã chạy thử) |

**Qua test nhưng sai với khách này:**

- Thêm `it:Ban gi_m _c/` hay `legal:Ban gi_m _c/` "để IT kiểm thử": test không có user nhóm `it` nên không bắt được, nhưng
  vi phạm chính sách "Ban giám đốc chỉ quản trị" (biến thể thêm cho `legal` thì test bắt: an thấy 4 tài liệu).
- Yêu cầu IT thêm mapper vào client scope dùng chung của realm (vd. `profile`): đúng về kỹ thuật nhưng IT chỉ nhận thay
  đổi trên client `quillo`, và nó làm **mọi** ứng dụng trong realm nhận danh sách nhóm (lộ cơ cấu tổ chức cho app không
  cần).
- Đổi tên thư mục trên file share sang ASCII cho khớp ACL: dữ liệu của khách không phải của bạn; lần đồng bộ sau với
  connector giữ đường dẫn sẽ tạo bản sao.

## Bài học hiện trường

- "Đăng nhập được nhưng không thấy gì" gần như luôn là **authorization**, không phải authentication: token hợp lệ, phần
  ánh xạ danh tính → quyền thiếu ở một trong hai đầu.
- Group claim là thứ phải **xin** IdP của khách (Keycloak: mapper; Entra ID: `groupMembershipClaims` và giới hạn ~200 nhóm
  trong token, quá thì phải gọi Graph; AD FS: claim rule). Đưa vào checklist trước buổi bật SSO, cùng redirect URI.
- Session UI của quillo giữ nhóm 8 giờ: sau khi IT thêm mapper, người dùng UI phải đăng xuất/đăng nhập lại mới thấy; token
  API thì có hiệu lực ngay ở token kế tiếp. Nói trước với khách để không có ticket thứ hai.
