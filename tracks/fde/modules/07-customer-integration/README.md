# Tích hợp hệ thống và dữ liệu của khách

Cài được sản phẩm lên máy khách mới là một nửa. Nửa còn lại là làm nó **sống trong hệ thống của khách**: người dùng đăng
nhập bằng tài khoản công ty và chỉ thấy đúng thứ họ được thấy; dữ liệu chảy vào từ file share, database, hệ thống cũ mà
không rời mạng của khách; secret đi theo chính sách của phòng bảo mật; và trước khi mở rộng, sản phẩm phải qua được bộ
câu hỏi đánh giá nhà cung cấp. Ở mỗi chỗ nối đó, phần của bạn chỉ là một nửa: IdP do IT quản, file share do phòng hành
chính sắp xếp, hệ thống cũ không ai dám sửa. Kỹ năng FDE ở đây là **đọc được dữ liệu thật ở chỗ nối**, sửa phần của
mình, và viết đúng yêu cầu cho phần của người khác.

Sau module này bạn sẽ:

- Kiểm một access token OIDC như một resource server (chữ ký qua JWKS, `iss`, `aud`, thời hạn, xoay khoá) và chẩn đoán
  SSO bằng token thật thay vì đoán cấu hình.
- Ánh xạ danh tính của IdP sang quyền trong sản phẩm, nói được OIDC, SAML và LDAP/AD khác nhau ở đâu khi nối.
- Viết connector dữ liệu chạy định kỳ: incremental, idempotent, xoá đúng, giữ đường dẫn cho phân quyền, không cần quyền
  root hay công cụ hệ thống của khách.
- Đọc export của hệ thống cũ đúng từng ký tự.
- Cấp secret theo chính sách của khách và chứng minh nó không lộ.
- Trả lời security questionnaire trung thực, thiết kế xử lý dữ liệu cá nhân trước khi index.

## 0. Cài đặt

Các bài dùng máy `lab-open` cùng hai dịch vụ "của IT khách" chạy phía host: Keycloak (IdP OIDC, realm `lawfirm`) và
Samba (file share `contracts`), bật qua `fdekit.customer_site(..., extra_services=("keycloak", "fileshare"))`. Hai bài
intermediate dùng snapshot dẫn xuất `07-customer-integration-quillo`: `lab-open` đang chạy quillo 1.0.0 bằng compose,
chưa bật SSO, inbox rỗng.

```bash
nice -n 15 uv run python -m fdekit prepare lab-open
nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
nice -n 15 uv run python -m fdekit derive 07-customer-integration-quillo
docker pull quay.io/keycloak/keycloak:26.8.1-1@sha256:a78d6b79572168cb25886b80a8b5b8d4ed4390743e3eecb810538683e209dd6b
docker pull ghcr.io/servercontainers/samba:smbd-only-a3.24.3-s4.23.8-r0@sha256:04fb3bd3da742ddb988f621e8c38b0dcbc26e7b4c438c9836abb43d937bc27e6
```

| Thành phần | Bản (ngày phát hành) | Ghi chú |
| --- | --- | --- |
| Keycloak | `26.8.1-1` (2026-10-23), ghim digest | ~20 s tới khi realm sẵn sàng; giới hạn 1024 MB |
| Samba | `4.23.8` trên Alpine (2026-10-22), ghim digest | Chỉ SMB2/SMB3, share chỉ đọc |
| `smbprotocol` | `1.17.0` (2026-07-07), kèm `pyspnego 0.12.4` | Client SMB thuần Python, đã có trong `pyproject.toml` của repo |
| `PyJWT`, `cryptography` | bản trong `uv.lock` | Kiểm JWT ở bài basic 01 |
| Snapshot `07-customer-integration-quillo` | dựng ~1 phút, ~2,8 GB trong `data/raw/fde-images/derived/` | Bundle hay script dựng đổi thì test skip kèm đúng lệnh `derive` |

Kiểm: `uv run python -c "import smbclient, jwt"` không lỗi; `uv run python -m fdekit derive --list` báo
`07-customer-integration-quillo ... có ...`. Gỡ: xoá `07-customer-integration-quillo-*.qcow2` trong
`data/raw/fde-images/derived/`, `docker image rm` hai image trên.

## 1. Chỗ nối với hệ thống của khách

Một triển khai on-prem thật có ít nhất bốn chỗ nối, mỗi chỗ có một chủ khác:

```mermaid
flowchart LR
    subgraph khach["Mạng của khách"]
        idp["IdP<br/>(Keycloak, Entra ID, AD FS)<br/>chủ: IT"]
        share[("File share / DB / S3 nội bộ<br/>chủ: phòng ban")]
        legacy["Hệ thống cũ<br/>chỉ xuất CSV<br/>chủ: không ai"]
        vault[("Vault / tệp secret<br/>chủ: bảo mật")]
        subgraph may["Máy chạy sản phẩm (chủ: bạn + IT)"]
            conn[connector] --> inbox[(inbox)]
            inbox --> app[sản phẩm]
        end
    end
    user[Người dùng] -->|đăng nhập| idp
    user -->|token| app
    app -->|discovery, JWKS| idp
    share -->|đọc, tài khoản dịch vụ| conn
    legacy -->|export theo lịch| conn
    vault -->|tệp| conn
    vault -->|tệp| app
```

Ba nguyên tắc dùng cho mọi chỗ nối:

1. **Dữ liệu không rời mạng của khách.** Connector chạy trên máy của khách, kéo dữ liệu về máy chạy sản phẩm, không qua
   máy của bạn hay dịch vụ cloud nào. "Mang về máy mình debug" là vi phạm, kể cả với một tệp.
2. **Quyền tối thiểu, đúng chủ.** Tài khoản dịch vụ chỉ đọc cho file share/DB; client riêng cho sản phẩm trong IdP; không
   xin quyền quản trị để "cho nhanh". Thứ bạn cần ở phía họ thì viết thành **yêu cầu**: cần gì, vì sao, phạm vi ảnh hưởng,
   cách kiểm sau khi làm.
3. **Tin dữ liệu, không tin cấu hình.** Tài liệu tích hợp của khách mô tả hệ thống họ *nghĩ* họ có. Token thật, tệp thật,
   chuỗi thật mà sản phẩm đã lưu mới là sự thật; mọi chẩn đoán bắt đầu từ đó.

## 2. SSO với OIDC: thứ thực sự đi qua dây

OpenID Connect là lớp danh tính trên OAuth 2.0. Với một ứng dụng web có backend (như quillo), luồng chuẩn là
**authorization code + PKCE**:

```mermaid
sequenceDiagram
    participant B as Trình duyệt
    participant A as Ứng dụng (client)
    participant I as IdP
    B->>A: GET /oidc/login
    A->>A: sinh state, nonce, code_verifier; code_challenge = SHA256(verifier)
    A-->>B: 302 tới authorization_endpoint (client_id, redirect_uri, scope=openid, state, nonce, code_challenge)
    B->>I: đăng nhập (mật khẩu, MFA: việc của IdP)
    I-->>B: 302 tới redirect_uri?code=…&state=…
    B->>A: GET /oidc/callback?code&state
    A->>I: POST token_endpoint (code, code_verifier, client secret)
    I-->>A: id_token (ai đăng nhập) + access_token (gọi API)
    A->>I: GET jwks_uri (cache theo kid)
    A->>A: kiểm chữ ký, iss, aud, exp, nonce → phiên
```

Những điểm hay gãy ở hiện trường:

- **Discovery** (`/.well-known/openid-configuration`) cho `issuer`, `authorization_endpoint`, `token_endpoint`,
  `jwks_uri`. IdP công bố URL theo hostname **nó được cấu hình**, không theo URL bạn gõ. Sau reverse proxy hay
  split-horizon DNS, máy chạy sản phẩm có thể nhận về URL nó không tới được, và chuỗi `issuer` phải khớp **từng ký tự**
  (scheme, cổng, `/` cuối) với claim `iss` của token.
- **`redirect_uri`** phải nằm trong danh sách IdP cho phép, đúng scheme/host/cổng/đường dẫn người dùng thật thấy (sau
  reverse proxy là URL công khai, không phải `127.0.0.1:8080`). Sai thì lỗi hiện ở trang của IdP, không phải ở ứng dụng.
- **ID token vs access token.** ID token dành cho client (`aud` = client id) để biết ai đăng nhập; access token dành cho
  resource server (API). Nhiều IdP phát access token dạng JWT (RFC 9068), nhưng **claim nào có trong mỗi loại do cấu hình
  IdP quyết định**: thấy claim trong ID token không có nghĩa API sẽ thấy nó trong access token.
- **Resource server kiểm gì** (RFC 8725 là danh sách lỗi đã từng xảy ra):
  1. `alg` do bạn quyết (danh sách RS/PS/ES), không lấy từ header: chặn `alg: none` và nhầm `HS256` + khoá công khai.
  2. Khoá chọn theo `kid` trong JWKS; `kid` lạ thì tải lại JWKS một lần (IdP xoay khoá) có giới hạn tần suất.
  3. Chữ ký, rồi mới tới `iss` (so nguyên chuỗi), `aud` (chứa client id của bạn, chặn token cấp cho app khác cùng realm),
     `exp`/`nbf`/`iat` với độ lệch đồng hồ nhỏ (30–60 s). Máy air-gapped không NTP lệch vài phút là chuyện thường: sửa
     NTP, đừng nới leeway.
- **Client secret** là secret: theo mục 5. Client công khai (SPA, CLI) không có secret, dựa vào PKCE.

Công cụ chẩn đoán đầu tiên luôn là **một token thật**: lấy bằng luồng mà người dùng dùng (hoặc password grant nếu IT
bật cho môi trường thử), giải mã payload (base64url), đọc claim. Phần lớn ticket "đăng nhập rồi nhưng…" trả lời được bằng
việc so payload đó với thứ ứng dụng đang chờ.

## 3. Từ danh tính tới quyền: claim nhóm, SAML, LDAP/AD

Authentication trả lời "ai", authorization trả lời "được làm gì". SSO chỉ lo phần đầu; phần sau là ánh xạ **thuộc tính
từ IdP** (nhóm, vai trò, phòng ban) sang quyền trong sản phẩm. Với quillo, đó là claim nhóm (`QUILLO_OIDC_GROUPS_CLAIM`)
và ACL theo thư mục (`QUILLO_ACL`). Điểm cần kiểm khi nối:

- **Claim có trong token không, tên gì, dạng gì.** Đó là cấu hình phía IdP (Keycloak: protocol mapper hoặc client scope
  của client; Entra ID: `groupMembershipClaims` trong app registration; AD FS: claim rule), không phải mặc định chung. Nhóm
  có thể đến dưới dạng tên, đường dẫn (`/legal/hop-dong` với nhóm lồng nhau), hay GUID (Entra ID trả object id của nhóm,
  không phải tên). Người dùng thuộc quá nhiều nhóm thì token bị cắt: Entra ID đưa tối đa 200 nhóm vào JWT, quá thì thay
  bằng "overage claim" và ứng dụng phải tự hỏi Microsoft Graph.
- **Tên ở hai đầu phải khớp chuỗi đã lưu.** Quy tắc ACL so với dữ liệu **sản phẩm đã lưu**, sau mọi bước chuẩn hoá của
  sản phẩm (làm sạch tên, chuẩn Unicode, chữ hoa thường). Viết ACL từ tài liệu của khách mà không nhìn dữ liệu đã lưu là
  đoán.
- **Thời điểm có hiệu lực.** Nhóm thường được "chụp" lúc đăng nhập: thêm người vào nhóm ở IdP thì phiên UI cũ không biết;
  thu hồi quyền cũng vậy. Biết sản phẩm giữ phiên bao lâu (quillo: 8 giờ) để nói trước với khách.
- **Ai được nhìn mọi thứ.** Tài khoản break-glass/token quản trị luôn tồn tại; ghi nó vào tài liệu bàn giao, đừng giấu.

| | OIDC | SAML 2.0 | LDAP/AD trực tiếp |
| --- | --- | --- | --- |
| Định dạng | JSON, JWT ký (JWS) | XML assertion ký (XML-DSig) | Giao thức thư mục; ứng dụng bind bằng mật khẩu người dùng |
| Đi qua | Redirect + gọi back-channel tới token endpoint | Trình duyệt POST assertion (không back-channel) | Ứng dụng nói thẳng với domain controller (389/636) |
| API/CLI | Bearer token, chuẩn | Không có token cho API, cần cơ chế khác | Ứng dụng phải giữ mật khẩu người dùng trong lúc bind |
| Nhóm | Claim do IdP cấu hình | Attribute trong assertion | `memberOf`; nhóm lồng nhau cần truy vấn riêng (`LDAP_MATCHING_RULE_IN_CHAIN`) |
| MFA | Ở IdP | Ở IdP | Không có (mật khẩu đi qua ứng dụng) |
| Lỗi hay gặp ở khách | `issuer`, redirect URI, claim thiếu, lệch đồng hồ | Xoay chứng chỉ ký, lệch đồng hồ, `NameID` sai định dạng | LDAPS với CA nội bộ, tài khoản bind hết hạn mật khẩu, timeout tới DC xa |

Khách chỉ có AD mà sản phẩm chỉ nói OIDC: đừng viết LDAP vào sản phẩm. Hỏi họ đã có AD FS/Entra ID chưa, hoặc dựng một
broker (Keycloak với LDAP user federation) do IT quản; sản phẩm vẫn chỉ nói OIDC.

## 4. Nguồn dữ liệu của khách và connector

Mỗi loại nguồn có một "cách đúng" để đọc mà không làm phiền chủ của nó:

- **Database**: đọc từ replica hay view do DBA tạo, bằng user chỉ `SELECT`, ngoài giờ cao điểm; incremental theo cột
  `updated_at` hay khoá tăng dần (cẩn thận bản ghi bị xoá: không có cột nào "nhớ" chúng, cần bảng tombstone hay CDC);
  không bao giờ `SELECT *` cả bảng lớn mỗi giờ.
- **File share SMB/NFS**: tài khoản dịch vụ chỉ đọc; máy khách thường không có `cifs-utils`/`smbclient` và bạn không có
  quyền mount, nên dùng client SMB thuần userland (như `smbprotocol`). mtime trên share do **máy ghi** đặt; đổi tên thư
  mục ở nguồn là xoá + thêm cả cây.
- **Object storage S3-compatible** (MinIO, Ceph RGW): liệt kê theo prefix, phát hiện đổi bằng ETag/`LastModified` (ETag
  của multipart upload không phải MD5 nội dung), endpoint và CA nội bộ, path-style addressing.
- **Export của hệ thống cũ**: thường là ảnh chụp toàn bộ, theo lịch, định dạng của phần mềm viết cho một máy Windows từ
  nhiều năm trước. Không có schema, không có bảng mã ghi trong tệp.

Dù nguồn là gì, connector tốt có cùng một hình:

```mermaid
flowchart TD
    list["Liệt kê nguồn<br/>(metadata rẻ: mtime, size, ETag, updated_at)"] --> diff{"So với state<br/>của lần trước"}
    diff -->|"không đổi"| skip[bỏ qua, không đọc nội dung]
    diff -->|"mới / metadata đổi"| read["Đọc + băm nội dung"]
    read --> same{"Băm trùng<br/>bản đã giao?"}
    same -->|có| meta[chỉ cập nhật state]
    same -->|không| deliver["Giao: tệp tạm → rename nguyên tử<br/>giữ đường dẫn tương đối"]
    diff -->|"có trong state, mất ở nguồn"| del["Báo xoá; gỡ bản còn chờ<br/>nếu đúng là bản mình giao"]
    deliver --> state[("state: ghi tạm + fsync + rename<br/>sau mỗi mục")]
    meta --> state
    del --> state
```

- **State thuộc về connector**, không suy ra từ đích (đích có thể bị bên khác dọn, như worker chuyển tệp khỏi inbox).
- **Idempotent**: chạy lại khi không có gì đổi thì không làm gì; chết giữa chừng thì lần sau làm tiếp đúng chỗ.
- **Giữ đường dẫn** vì phân quyền theo thư mục cần nó; quyết định trước khi giao xem đích chuẩn hoá tên thế nào.
- **Lỗi từng mục không làm hỏng cả lượt**; mã thoát phân biệt "có mục lỗi" với "không chạy được".

Văn bản từ hệ thống cũ cần hai bước mà Python 3 hay làm người ta quên vì "mặc định UTF-8":

1. **Bảng mã là giả thuyết phải chứng minh.** Một tệp byte không tự nói bảng mã. Tìm bằng chứng: hệ thống viết cho nền
   tảng nào, ngôn ngữ nào; giải mã thử và nhìn đúng những byte ≥ 0x80; đối chiếu với văn bản người dùng thấy trên màn hình
   gốc. Giải mã bằng bảng mã "chịu mọi byte" (như Latin-1) không bao giờ báo lỗi, nên nó là cách nhanh nhất để sinh rác
   lặng lẽ; dùng `errors="strict"` để sai thì dừng.
2. **Cùng một chữ có thể là nhiều chuỗi code point.** Unicode cho phép chữ có dấu ở dạng dựng sẵn (một code point) hoặc
   tổ hợp (chữ cơ sở + dấu); tên tệp từ macOS, một số bảng mã cũ và một số bộ gõ sinh dạng khác nhau. Hai chuỗi trông
   giống hệt nhau vẫn khác khi so `==`, khi tìm kiếm, khi băm. Chọn một dạng chuẩn (UAX #15: NFC là lựa chọn thông dụng
   cho văn bản) và chuẩn hoá ở biên vào.

Phần còn lại là định dạng địa phương: dấu phân cách `;` (nơi `,` là dấu thập phân), ô có xuống dòng bên trong, ngày
`dd/mm` hay `mm/dd` (tìm một bản ghi ngày > 12 để chứng minh), số có dấu phân cách nghìn. Đừng đọc CSV bằng `split`.

## 5. Secret theo chính sách khách

Một secret (mật khẩu DB, client secret OIDC, token API) có thể đến với ứng dụng bằng ba cách, và phòng bảo mật thường cho
phép đúng một:

| Cách | Lộ ở đâu | Ghi chú |
| --- | --- | --- |
| Tham số dòng lệnh | `/proc/<pid>/cmdline`: **mọi user** trên máy thấy qua `ps` (trừ `/proc` mount `hidepid`); audit `execve` ghi lại | Không bao giờ |
| Biến môi trường | `/proc/<pid>/environ` (cùng user, root), kế thừa sang mọi tiến trình con, `docker inspect`, `systemctl show`, crash report, support bundle chứa `env` | Tiện, dễ rò |
| Tệp | Quyền tệp kiểm soát được (0400/0600, chủ riêng), đường dẫn audit được, xoay bằng cách ghi lại tệp | Quy ước `*_FILE` |

Quy ước `*_FILE`: biến môi trường chỉ chứa **đường dẫn** (`POSTGRES_PASSWORD_FILE=/run/secrets/db`), ứng dụng đọc nội
dung tệp. Docker/Compose secrets mount vào `/run/secrets/`, Kubernetes mount Secret thành tệp, Vault Agent và Secrets
Store CSI driver ghi tệp và có thể xoay mà không restart (ứng dụng đọc lại tệp khi cần). Ứng dụng nên kiểm tệp trước khi
tin: tệp thường, không cho group/other đọc, mở không theo symlink và kiểm trên chính fd.

Đọc đúng chỗ mới là nửa đầu. Secret còn rò qua:

- **Log**: dòng debug in header/URL/cấu hình; URL có userinfo (`https://user:pass@host`) hay query (`?token=`).
- **Thông báo lỗi**: exception của thư viện và của tiến trình con chứa đúng thứ bạn đưa cho nó (URL đầy đủ, argv); dịch
  vụ ở đầu kia đôi khi lặp lại token trong phản hồi lỗi. Bắt lỗi ở biên, tự viết thông báo, lọc secret khỏi mọi chuỗi
  ra ngoài; không để traceback ra stderr của một công cụ chạy theo lịch.
- **Tiến trình con**: gọi `curl` với header trên argv là đặt secret vào `ps`; truyền qua env của tiến trình con là đặt
  vào `/proc/<pid>/environ`. Nếu buộc dùng chương trình ngoài, đưa secret qua tệp hoặc stdin.
- **Core dump, swap, `strace` của người có quyền**: thuộc chính sách hệ thống của khách; ghi vào câu trả lời
  questionnaire thay vì tự chế cơ chế.

Kiểm chứng bằng **secret gieo ngẫu nhiên**: sinh một giá trị mới mỗi lần, chạy cả đường thành công lẫn mọi đường lỗi,
rồi tìm giá trị đó trong output, log, tệp, `/proc`. Grep `password` không chứng minh gì.

## 6. Security questionnaire, data residency và dữ liệu cá nhân

Trước khi mở rộng, phòng bảo mật của khách gửi bộ câu hỏi đánh giá nhà cung cấp (bản tự soạn, hoặc dựa trên mẫu như CAIQ
của Cloud Security Alliance hay SIG). Câu trả lời thường đi vào phụ lục hợp đồng, nên nó là **cam kết**, không phải tài
liệu marketing:

- **Đúng sự thật với bản đang triển khai**: "Có" chỉ khi có trong code/cấu hình; chỗ thiếu ghi "Không"/"Một phần" kèm
  biện pháp bù và kế hoạch. Phòng bảo mật sẽ tìm ra chỗ bạn giấu ở buổi kiểm tra kỹ thuật.
- **Bằng chứng khách tự kiểm được**: lệnh, tệp cấu hình, kết quả kiểm thử, không phải "chúng tôi cam kết".
- **Chia trách nhiệm**: mã hoá đĩa, MFA, thời gian giữ log, sao lưu ngoài site thường là của khách; không gọi ra ngoài,
  kiểm token, che secret là của sản phẩm; nhiều thứ là chung.
- **Đi theo dữ liệu**: liệt kê mọi nơi dữ liệu nằm lại (bản gốc, bản đã xử lý, chỉ mục, prompt, log, backup, bản export,
  support bundle). Câu hỏi về mã hoá, xoá, lưu giữ đều trả lời theo danh sách đó.

**Data residency** với sản phẩm on-prem không chỉ là "máy đặt ở Việt Nam": model chạy local, không telemetry, không cập
nhật tự động, và quy trình hỗ trợ của chính bạn (support bundle, screen-share) cũng không mang dữ liệu ra.

**Dữ liệu cá nhân trước khi index**: chỉ mục vector và prompt là nơi khó "che" nhất sau khi đã tạo (embedding của một
đoạn có tên người không xoá tên được), nên quyết định xử lý phải nằm **trước** bước index: phát hiện theo loại thực thể
(mẫu có cấu trúc + kiểm tra hợp lệ cho số giấy tờ, số điện thoại; NER chạy local cho tên, địa chỉ), biến đổi theo nhóm
người dùng (đầy đủ/đã che/bí danh nhất quán có khoá do khách giữ), đo bằng bộ có nhãn, và có đường xoá theo yêu cầu.
Khung pháp lý ở Việt Nam là Luật Bảo vệ dữ liệu cá nhân (thông qua năm 2025, hiệu lực từ 01/01/2026) cùng các văn bản
hướng dẫn, trước đó là Nghị định 13/2023/NĐ-CP: diễn giải áp dụng do phòng pháp chế của khách quyết, việc của bạn là thiết
kế cho phép họ thực thi được.

## 7. Ôn nhanh: governance dữ liệu và nạp tài liệu cho RAG

Module giả định bạn đã quen phân loại dữ liệu, masking, kiểm soát truy cập theo vai trò ở tầng dữ liệu (track Data
Engineer: [10 · Security & governance](../../../data-engineer/modules/10-security-governance/README.md)) và đường nạp
tài liệu của RAG (trích văn bản, chunk, embedding, truy hồi: track AI Engineer
[13 · RAG](../../../ai-engineer/modules/13-rag/README.md); rủi ro dữ liệu trong hệ thống LLM:
[19 · AI safety & security](../../../ai-engineer/modules/19-ai-safety-security/README.md)). Điểm khác ở đây: dữ liệu và
danh tính đều là **của khách**, nằm trong hệ thống bạn không quản, và mọi quyết định về chúng phải viết thành yêu cầu
hoặc câu trả lời người khác duyệt được.

## 8. Tài liệu tham khảo

- OAuth 2.0 và OIDC: [RFC 6749 OAuth 2.0](https://www.rfc-editor.org/rfc/rfc6749),
  [RFC 7636 PKCE](https://www.rfc-editor.org/rfc/rfc7636), [RFC 7519 JWT](https://www.rfc-editor.org/rfc/rfc7519),
  [RFC 7517 JWK](https://www.rfc-editor.org/rfc/rfc7517), [RFC 8725 JWT Best Current Practices](https://www.rfc-editor.org/rfc/rfc8725),
  [RFC 9068 JWT Profile for OAuth 2.0 Access Tokens](https://www.rfc-editor.org/rfc/rfc9068),
  [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html),
  [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html).
- IdP: [Keycloak Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/) (clients, protocol
  mappers, client scopes, keys), [Keycloak Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/),
  [Microsoft Entra: optional claims và groups claim](https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims),
  [SAML 2.0 Core (OASIS)](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf).
- Dữ liệu: [smbprotocol](https://github.com/jborean93/smbprotocol), [Python codecs: standard encodings](https://docs.python.org/3/library/codecs.html#standard-encodings),
  [Python csv](https://docs.python.org/3/library/csv.html), [Unicode UAX #15: Normalization Forms](https://unicode.org/reports/tr15/).
- Secret: [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html),
  [Docker Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/),
  [Postgres image: Docker Secrets (`_FILE`)](https://hub.docker.com/_/postgres),
  [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html) (`cmdline`, `environ`, `hidepid`).
- Đánh giá nhà cung cấp: [CSA Cloud Controls Matrix và CAIQ](https://cloudsecurityalliance.org/research/cloud-controls-matrix).
- [roadmap.sh: Forward Deployed Engineer](https://roadmap.sh/forward-deployed-engineer).
