# Lời giải: security questionnaire của công ty luật

Bài mẫu dưới đây đạt 19/20 theo rubric trong README (trừ 1 điểm "bằng chứng" ở Q12 vì chưa có bộ kiểm thử red-team, xem
module 09). Mỗi câu theo khung Trả lời / Chi tiết / Bằng chứng / Trách nhiệm. Sự thật đối chiếu với quillo 1.0.0:
`compose.yaml`, `compose.sso.yaml`, `src/quillo/*.py`, README sản phẩm.

## Bài mẫu

**Q1. Luồng mạng.** *Không* gửi dữ liệu ra ngoài. LLM và embedding là llama.cpp server chạy trong máy, model GGUF nằm
trong bundle; không telemetry, không kiểm bản quyền, không tự cập nhật (cập nhật = bundle mới do bạn chép vào). Kết nối
vào: chỉ cổng api (`QUILLO_BIND:QUILLO_PORT`, mặc định `127.0.0.1:18080`). Kết nối ra: Postgres/llm/embed trong mạng
compose nội bộ; IdP (discovery + JWKS + token endpoint) khi bật SSO; file share (connector, tài khoản chỉ đọc).
*Bằng chứng:* `docker compose config` (chỉ `api` có `ports`); `ss -tnp` trên máy chủ khi đang hỏi đáp; chạy được trên
máy không có route ra internet (đã cài air-gapped ở module 03). *Trách nhiệm:* vendor (sản phẩm không gọi ra ngoài);
khách (firewall chặn egress của máy chủ như lớp phòng thủ thứ hai).

**Q2. At rest.** *Một phần.* Lưu ở: volume Docker `quillo_db-data` (Postgres: văn bản đoạn trích, embedding, tên tệp);
`inbox/done/` (bản gốc tệp đã nạp, giữ nguyên); `inbox/failed/`; bản sao lưu do `ops/backup.sh` tạo. Quillo **không**
tự mã hoá ở tầng ứng dụng; mã hoá at rest dựa vào mã hoá đĩa/volume của máy chủ (LUKS, BitLocker trên hypervisor,
SAN), khoá do khách quản. *Bằng chứng:* `docker volume inspect quillo_db-data`, `ls inbox/done`, `lsblk -f` (thấy
`crypto_LUKS`). *Trách nhiệm:* khách (mã hoá đĩa, giữ khoá); vendor (ghi rõ vị trí dữ liệu, quyền `inbox` 0750 uid 10001,
`.env` 0600). *Kế hoạch:* tuỳ chọn xoá bản gốc trong `done/` sau khi nạp: yêu cầu đã gửi product.

**Q3. In transit.** *Một phần.* api phục vụ HTTP, mặc định chỉ trên `127.0.0.1`; truy cập từ máy khác phải qua reverse
proxy TLS của khách (chứng chỉ CA nội bộ); khi đó api phải chạy uvicorn với `--proxy-headers` để cookie có
cờ `Secure` (mục bảo mật của README sản phẩm). Giữa các container
trên cùng máy: HTTP/TCP không mã hoá trong mạng bridge nội bộ (không rời máy). Tới IdP: HTTPS với CA nội bộ qua
`QUILLO_OIDC_CA_FILE`. *Bằng chứng:* `compose.yaml` (`ports` của api), `curl -v https://quillo.<domain>/healthz` qua
proxy. *Trách nhiệm:* chung (khách cấp chứng chỉ và proxy; FDE cấu hình).

**Q4. Xác thực.** *Có (SSO), Một phần (tài khoản tĩnh).* OIDC authorization code + PKCE (S256) cho UI, Bearer access
token cho API; kiểm chữ ký JWKS (chỉ RS/PS/ES), `iss`, `aud`/`azp`, `exp` (lệch ≤ 60 s). MFA do IdP thực thi (quillo
không thấy và không bỏ qua được bước MFA). Có **một token tĩnh** `QUILLO_ADMIN_TOKEN` (quản trị, thấy mọi tài liệu):
dùng làm tài khoản break-glass; lưu trong `.env` 0600, đổi token là vô hiệu mọi phiên. Không có tài khoản người dùng
cục bộ. *Bằng chứng:* `curl -H "Authorization: Bearer <token sai chữ ký>" /api/me` ⇒ 401; log `token OIDC bị từ chối`.
*Trách nhiệm:* khách (chính sách MFA, vòng đời tài khoản ở IdP; giữ token quản trị như mật khẩu root); vendor (kiểm token).

**Q5. Phân quyền.** *Có.* Nhóm lấy từ claim của IdP; ACL theo thư mục (`QUILLO_ACL`) áp **trong câu truy vấn vector**
nên đoạn của phòng khác không vào prompt của LLM và không thành trích dẫn. Tài liệu ngoài mọi thư mục ACL chỉ quản trị
thấy. Giới hạn: extension của khách (`ExtensionContext.db_query`) không áp ACL; nhóm của phiên UI được giữ 8 giờ (thu hồi
quyền có hiệu lực với UI sau tối đa 8 giờ, hoặc ngay khi đổi token quản trị). *Bằng chứng:* kiểm thử chấp nhận với 3
user (bài intermediate 01): mỗi người chỉ thấy thư mục của mình qua `/api/documents` và `/api/ask`. *Trách nhiệm:* chung
(khách quản nhóm ở IdP và cây thư mục; FDE ánh xạ ACL).

**Q6. Nhật ký.** *Một phần.* Log JSON một dòng mỗi sự kiện ra stdout của container (`docker compose logs`): truy cập
(phương thức, đường dẫn, mã trạng thái, thời gian; **không** có nội dung câu hỏi hay câu trả lời), đăng nhập SSO (tên
người dùng, nhóm), tài liệu đã nạp (**tên tệp**, `doc_id`). Tên tệp và tên người dùng là dữ liệu cá nhân (vd.
`NDA Nguyễn Văn A.pdf`). Nơi lưu và thời gian giữ do log driver của Docker/journald của khách quyết định. *Bằng chứng:*
`docker compose logs api worker | head`. *Trách nhiệm:* khách (giữ log, phân quyền đọc log, chuyển về SIEM); vendor (không
ghi nội dung tài liệu/câu hỏi, không ghi token).

**Q7. Secret.** *Một phần.* Mật khẩu database và token quản trị trong `.env` (0600, chỉ user vận hành); client secret OIDC
trong **tệp** `oidc/client-secret` (chủ 10001, 0400) mount chỉ đọc, không qua biến môi trường; connector đọc mật khẩu
file share từ tệp. Chưa tích hợp Vault trực tiếp; dùng được Vault Agent/CSI ghi tệp. Xoay: đổi tệp/biến rồi `docker
compose up -d` (client secret, token quản trị); mật khẩu Postgres cần đổi cả trong DB. *Bằng chứng:* `stat -c '%a %U'
.env oidc/client-secret`; `docker inspect quillo-api-1 --format '{{json .Config.Env}}'` không có client secret.
*Trách nhiệm:* chung. *Kế hoạch:* hỗ trợ `QUILLO_DB_PASSWORD_FILE`/`QUILLO_ADMIN_TOKEN_FILE`: yêu cầu gửi product.

**Q8. Chuỗi cung ứng.** *Một phần.* Bundle có `manifest.json` (sha256 từng tệp, image ghim digest); `release.py verify`
phát hiện tệp hỏng/thiếu/thừa; Python dependency khoá hash (`pip --require-hashes`). Manifest nằm trong bundle nên không
chống sửa có chủ đích: vendor gửi sha256 của chính tệp bundle qua kênh riêng (email/ticket). Chưa có SBOM kèm bundle và
chưa ký bundle; không cam kết SLA vá lỗi trong phụ lục này (chưa có quy trình được phê duyệt), sẽ đề xuất riêng.
*Bằng chứng:* `sha256sum quillo-1.0.0.tar` so với sha trong ticket; `release.py verify`. *Trách nhiệm:* vendor.

**Q9. Mô hình AI.** Qwen2.5-0.5B-Instruct (GGUF Q4_K_M) cho trả lời, nomic-embed-text-v1.5 cho embedding, chạy CPU trong
máy chủ của khách. **Không** huấn luyện hay tinh chỉnh trên dữ liệu khách; vendor không nhận dữ liệu. Câu hỏi không được
lưu vào database hay log (chỉ đường dẫn `/api/ask` trong log truy cập). *Bằng chứng:* sha256 model trong
`manifest.json`; schema `migrations/0001_init.sql` (không có bảng câu hỏi). *Trách nhiệm:* vendor.

**Q10. Xoá dữ liệu.** *Một phần.* Bản 1.0.0 **không có API xoá từng tài liệu**: tài liệu gỡ khỏi nguồn được connector
báo (`deleted`), quản trị xoá bằng SQL theo `doc_id` (kèm `done/`) theo runbook. Chấm dứt hợp đồng: `docker compose down
-v` (xoá volume DB), xoá `inbox/`, bản sao lưu, image; biên bản xoá kèm lệnh và output. *Trách nhiệm:* chung. *Kế hoạch:*
API xoá: yêu cầu gửi product.

**Q11. Truy cập của vendor.** Không có truy cập từ xa thường trực, không có tài khoản ẩn. FDE chỉ truy cập qua phương
thức khách cấp (VPN/bastion, tài khoản riêng, có thời hạn), hoặc khách tự chạy lệnh qua screen-share. Dữ liệu chẩn đoán
là support bundle khách xem trước khi gửi: cấu hình đã che secret, log; không có tài liệu hay database. *Trách nhiệm:*
khách (cấp/thu hồi truy cập); vendor (quy trình, che secret).

**Q12. Rủi ro AI.** *Một phần.* Nội dung tài liệu đi thẳng vào prompt: tài liệu độc có thể lái câu trả lời (prompt
injection); ACL chặn được việc *đọc chéo* phòng ban nhưng không chặn được việc tài liệu trong cùng phạm vi lái câu trả
lời. Câu trả lời luôn kèm trích dẫn đoạn gốc để người dùng kiểm; model nhỏ có thể trả lời sai. Biện pháp: chỉ nạp từ
nguồn của khách, đánh giá trên dữ liệu khách và bộ red-team trước khi mở rộng (kế hoạch nghiệm thu). *Trách nhiệm:* chung.

## Rubric chi tiết (người chấm)

| Tiêu chí | 0 | Một nửa | Đủ |
| --- | --- | --- | --- |
| Đúng sự thật (6) | Có lỗi loại trừ | Đúng nhưng mơ hồ ở ≥ 3 câu ("có mã hoá") | Mọi câu khớp code/cấu hình; ghi rõ giới hạn (token tĩnh, `done/`, tên tệp trong log, extension không ACL) |
| Bằng chứng (4) | Không có | 4–7 câu có lệnh/tệp | ≥ 8 câu có lệnh khách tự chạy được |
| Trách nhiệm (3) | Không chia | Chia nhưng đẩy hết cho khách | Chia đúng: đĩa/MFA/log retention là khách; không gọi ra ngoài/kiểm token/che secret là vendor |
| Chỗ thiếu (4) | Giấu | Thừa nhận, không biện pháp | Thừa nhận + biện pháp bù hiện có + yêu cầu product có tên |
| Văn phong (3) | Quảng cáo, thuật ngữ rỗng | Dài, lặp | Ngắn, cụ thể, đọc được trong 10 phút |

## Sai lầm thường gặp

- "Dữ liệu được mã hoá AES-256": Postgres không bật TDE, quillo không mã hoá; câu này sai và thành cam kết hợp đồng.
- Quên `inbox/done/`: bản gốc tài liệu vẫn nằm trên đĩa sau khi nạp.
- "Log không chứa PII": tên tệp hợp đồng và tên người dùng là PII.
- Trả lời Q4 mà không nhắc token quản trị tĩnh: phòng bảo mật sẽ tìm thấy nó trong `.env` ở buổi kiểm tra.
- Trả lời Q9 bằng "chúng tôi dùng AI an toàn": họ hỏi model gì, chạy ở đâu, dữ liệu đi đâu.
