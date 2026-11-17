---
title: "Hiện trường: SSO của công ty luật, đăng nhập được mà không thấy gì"
level: intermediate
services: []
files:
  - path: starter/sso.env
    note: Cấu hình SSO đồng nghiệp đã bật; bạn sửa
  - path: starter/idp-request.json
    note: Yêu cầu gửi IT khách cho Keycloak (đang rỗng); bạn viết
  - path: tests/test_sso_acl.py
    note: Không sửa; chạy thẳng tệp này để dựng cảnh điều tra
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - nice -n 15 uv run python -m fdekit derive 07-customer-integration-quillo
  - uv run pytest tracks/fde/modules/07-customer-integration/exercises/intermediate/01-sso-acl -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Công ty luật chạy quillo trên một máy lab của phòng IT để thử với nhân viên thật. Tài liệu đã được đồng bộ từ file share
của khách vào inbox, giữ nguyên cây thư mục của từng phòng. Đồng nghiệp của bạn bật SSO với Keycloak của khách và cấu
hình phân quyền theo thư mục, rồi bay sang khách khác. Sáng thứ Ba, IT khách gửi ticket. Việc của bạn: tìm ra vì sao,
sửa phần thuộc về quillo, và viết đúng yêu cầu cho phần thuộc về IT khách (bạn không có quyền quản trị IdP của họ).

## Đề bài

Máy `lab-open` (Ubuntu 22.04, Docker, có sudo) đang chạy quillo 1.0.0 bằng compose ở `/home/fde/quillo-1.0.0` (snapshot
dẫn xuất `07-customer-integration-quillo`). Keycloak của khách: `http://10.0.2.102:8080` nhìn từ máy đó, realm `lawfirm`,
client confidential `quillo` (client secret IT đã giao), nhóm `legal`, `finance`, `it`; user `an` thuộc `legal`, `binh`
thuộc `finance`, `chi` thuộc cả hai. Cách bật SSO và ACL của quillo ở mục "SSO (OIDC) và ACL theo thư mục" trong
[README sản phẩm](../../../../../product/README.md).

Tài liệu trong inbox (đồng bộ từ share `\\fileserver\contracts`) và chính sách của khách:

| Thư mục trên file share | Ai được xem trong quillo |
| --- | --- |
| `Pháp chế/` (mọi thư mục con) | nhóm `legal` |
| `Tài chính/` | nhóm `finance` |
| `Ban giám đốc/` | chỉ quản trị (token `QUILLO_ADMIN_TOKEN`), không nhóm SSO nào |

Ticket của IT khách:

> Đã bật đăng nhập bằng tài khoản công ty. Anh An (pháp chế) và chị Bình (kế toán) đăng nhập được nhưng không thấy tài
> liệu nào, hỏi gì cũng không có trích dẫn. Tài khoản admin thì vẫn thấy đủ.

Bạn nộp hai tệp trong `starter/`:

1. **`sso.env`**: các dòng `KHOÁ=giá_trị` cho quillo, chỉ được dùng `QUILLO_OIDC_ISSUER`, `QUILLO_OIDC_CLIENT_ID`,
   `QUILLO_OIDC_GROUPS_CLAIM`, `QUILLO_ACL`, `QUILLO_OIDC_CA_FILE` (dòng trống và dòng `#` được bỏ qua). Không chứa
   client secret.
2. **`idp-request.json`**: những thay đổi bạn cần IT làm trên Keycloak (có thể là không có gì), dạng

   ```json
   {"client": "quillo", "changes": [{"type": "...", "why": "lý do gửi IT", ...}]}
   ```

   IT chỉ nhận tối đa 5 thay đổi, mỗi thay đổi có `why` không rỗng, và chỉ ba loại, tất cả chỉ trên client `quillo`:
   `add-protocol-mapper` (kèm `"mapper"`: một ProtocolMapperRepresentation `openid-connect` của Keycloak admin REST API,
   `config` chỉ gồm chuỗi), `add-default-client-scope` (kèm `"scope"`: tên một client scope có sẵn trong realm),
   `set-redirect-uris` (kèm `"uris"`: mảng URL đầy đủ dạng `scheme://host/đường-dẫn`, **không** có ký tự đại diện `*`;
   thay toàn bộ danh sách hiện có). IT không đổi user, nhóm, realm hay client khác.

Test làm lại đúng cảnh trên rồi áp bài của bạn, theo thứ tự:

1. Boot snapshot với Keycloak mới (`fdekit.customer_site("lab-open", base=..., memory_mb=3072, forwards=(18080,),
   extra_services=("keycloak",))`), chờ quillo trả `/healthz` 200.
2. Đặt 6 tài liệu vào inbox theo cây thư mục ở bảng trên (nội dung sinh mới mỗi lần), chờ worker nạp xong.
3. Trong `/home/fde/quillo-1.0.0`: xoá khỏi `.env` các dòng có khoá xuất hiện trong `sso.env` của bạn hoặc thuộc
   `QUILLO_OIDC_ISSUER`, `QUILLO_OIDC_CLIENT_ID`, `QUILLO_ACL`, `QUILLO_OIDC_GROUPS_CLAIM`, nối `sso.env` vào cuối;
   ghi client secret IT giao vào `oidc/client-secret` (chủ 10001, quyền 0400) như README sản phẩm;
   `docker compose -f compose.yaml -f compose.sso.yaml up -d`; chờ `/healthz` 200 (≤120 s).
4. Đóng vai IT: áp `idp-request.json` qua admin REST API của Keycloak.
5. Lấy access token thật của `an`, `binh`, `chi` (password grant của client `quillo`) và kiểm như mục Tiêu chí.

Cả bài ~40 s trên máy của repo. Dựng đúng cảnh này để tự điều tra (in lệnh SSH, URL quillo và Keycloak phía host, mật
khẩu user, và **chỉ trong lab** tài khoản admin Keycloak để bạn thử trước khi viết yêu cầu cho IT):

```bash
PYTHONPATH=. uv run python tracks/fde/modules/07-customer-integration/exercises/intermediate/01-sso-acl/tests/test_sso_acl.py
# --apply-idp: áp luôn idp-request.json của bạn như IT; --no-sso: giữ quillo như trong snapshot
```

## Tiêu chí đạt

`test_sso_users_see_their_folders`:

- `sso.env` và `idp-request.json` đúng định dạng trên; compose với cấu hình của bạn lên và `/healthz` trả `200`; IT áp
  được mọi thay đổi (Keycloak trả 2xx).
- Token quản trị vẫn thấy đủ 6 tài liệu.
- Token SSO của `an`, `binh`, `chi` được quillo nhận (`GET /api/me` trả `200`).
- `GET /api/documents`: `an` thấy **đúng** 3 tài liệu `Pháp chế/`, `binh` đúng 2 tài liệu `Tài chính/`, `chi` đúng 5
  tài liệu của hai thư mục đó; không ai trong ba người thấy `Ban giám đốc/`.
- `POST /api/ask` của `an` có trích dẫn, và mọi trích dẫn thuộc `Pháp chế/`; mọi trích dẫn của `binh` thuộc `Tài chính/`.

## Gợi ý

### Gợi ý 1

Tách câu hỏi làm hai nửa: quillo nhận ra người gọi là ai và thuộc nhóm nào; rồi tài liệu nào khớp với nhóm đó. README
sản phẩm có một endpoint trả lời riêng nửa thứ nhất.

### Gợi ý 2

Đừng tin cấu hình, hãy xem dữ liệu: token thật mà Keycloak cấp, và dữ liệu thật mà quillo đã lưu. So từng ký tự với cái
cấu hình đang giả định.

### Gợi ý 3

Có thể có hơn một nguyên nhân, và nguyên nhân sau chỉ lộ ra khi nguyên nhân trước đã hết. Sửa một chỗ, kiểm lại bằng
token của từng user, rồi mới sang chỗ tiếp theo.
