# Lời giải: chính sách container image cho Olist

Bài Advanced không có một đáp án duy nhất. Reviewer chấm theo việc chính sách có **thực thi được** không: mỗi quy tắc có chỗ
kiểm tự động, mỗi con số có lý do, và kế hoạch triển khai không làm đứng 12 team vào ngày đầu. Dưới đây là các quyết định cốt
lõi, rubric, và một chính sách mẫu đã chạy qua test.

## Các quyết định cốt lõi

- **Danh sách image nền ngắn, do platform team sở hữu.** 9 image nền cho cùng ngôn ngữ nghĩa là 9 lịch vá. Mỗi ngôn ngữ một
  image build và một image runtime, ghim digest, Renovate mở PR khi digest mới xuất hiện (thường hằng tuần vì image chính thức
  được build lại khi distro vá). Team cần image khác thì xin thêm vào danh sách, không tự dùng.
- **Thời hạn vá theo mức độ và có bản vá hay không.** CRITICAL có bản vá: 7 ngày; HIGH có bản vá: 30 ngày (khớp mức phổ biến
  của PCI DSS và nhiều khung kiểm toán). Lỗ hổng chưa có bản vá không chặn (không ai làm gì được) nhưng có dashboard và rà
  soát hằng tháng. MEDIUM/LOW: backlog, gom vào lần rebuild image nền.
- **Gate hai tầng.** CI chặn image **mới** vi phạm (HIGH/CRITICAL có bản vá chưa có ngoại lệ). Quét định kỳ image **đang chạy**
  (CVE mới công bố cho image không đổi) mở ticket kèm hạn theo bảng, không chặn deploy hotfix.
- **Ngoại lệ là dữ liệu, không phải tin nhắn Slack.** `.trivyignore.yaml` trong repo của service: purl cụ thể, `statement` có
  bằng chứng, `expired_at` tối đa 90 ngày, PR được security duyệt (CODEOWNERS). Đếm và công khai số ngoại lệ theo team.
- **Truy vết image tới commit.** Nhãn OCI (`org.opencontainers.image.revision`, `.source`), tag bất biến theo commit SHA, deploy
  theo digest, SBOM và provenance (SLSA) đính kèm image, ký bằng cosign keyless (OIDC của GitHub Actions), admission controller
  (Kyverno hoặc Gatekeeper, hoặc Sigstore policy-controller) chỉ nhận image đã ký từ registry chung.
- **Runtime mặc định an toàn, ngoại lệ phải xin.** `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`,
  `capabilities.drop: [ALL]`, seccomp `RuntimeDefault`: chính là Pod Security Standard `restricted` (module 11). Docker socket bị
  cấm hoàn toàn; 4 service đang mount phải có kế hoạch thay thế (xem Advanced 02).
- **Lộ bí mật là sự cố, không phải lỗi build.** Khoá trong `.env` đã ở trong image trên registry phải được thu hồi và cấp mới
  ngay; quét bí mật (`trivy --scanners secret`, gitleaks) trong CI chặn tái diễn.
- **Triển khai theo pha.** Pha 1 (tuần 1-4) chỉ báo cáo và dashboard theo team; pha 2 (tháng 2) chặn image mới với CRITICAL có
  bản vá, `latest`, root; pha 3 (quý 2) chặn HIGH có bản vá, bắt buộc ký và digest ở admission. Tồn đọng 41 HIGH/image: phần lớn
  biến mất chỉ bằng đổi sang image nền đã duyệt và rebuild; phần còn lại vào backlog có hạn.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Image nền và ghim digest | 15 | Danh sách ngắn theo ngôn ngữ và vai trò (build/runtime), digest, người sở hữu, cơ chế cập nhật tự động (Renovate), lý do chọn từng image |
| Quy tắc Dockerfile thực thi được | 15 | Non-root có UID số, multi-stage, không `latest`, HEALTHCHECK hoặc probe, không bí mật trong layer, `.dockerignore`; mỗi quy tắc gắn công cụ kiểm (hadolint, conftest, trivy) |
| Thời hạn vá và gate | 15 | Thời hạn theo mức độ và trạng thái bản vá có lý do; tách gate build và quét định kỳ; xử lý lỗ hổng chưa có bản vá; DB trivy cũ thì sao |
| Ngoại lệ | 10 | Khoanh phạm vi, bằng chứng, người duyệt, tự hết hạn, đếm và công khai; nhắc VEX cho tuyên bố từ vendor |
| Chuỗi cung ứng | 15 | Tag bất biến, deploy theo digest, SBOM, ký và verify ở admission, provenance, truy vết commit, registry duy nhất |
| Runtime | 10 | Non-root, read-only rootfs, drop capability, no-new-privileges, giới hạn tài nguyên, cấm docker.sock và privileged, khớp Pod Security `restricted` |
| Triển khai và đo lường | 15 | Các pha có ngày, chế độ báo cáo trước khi chặn, xử lý tồn đọng, metric (tỷ lệ tuân thủ theo team, tuổi lỗ hổng, số ngoại lệ), xử lý sự cố `.env` |
| Rủi ro | 5 | Gate bị lách hoặc tắt, nghẽn ở platform team 3 người, chặn nhầm hotfix lúc sự cố (có đường break-glass có log) |

Trừ điểm: cho phép `latest` hay không digest ở production (−10); thời hạn CRITICAL có bản vá trên 14 ngày (−10, test chặn trên 7);
ngoại lệ không hết hạn (−10); chặn mọi thứ từ ngày đầu mà không có pha báo cáo (−5).

## Chính sách mẫu

`````markdown
# Chính sách container image của Olist

## 1. Phạm vi và nguyên tắc

Chính sách áp dụng cho mọi image do Olist build và chạy ở staging và production: service, job định kỳ, image dùng làm runner
hay công cụ trong CI. Platform team sở hữu chính sách, danh sách image nền và các gate; mỗi team sản phẩm sở hữu Dockerfile,
ngoại lệ và việc vá image của mình. Nguyên tắc: (1) mọi thứ chạy production truy vết được tới một commit và một digest; (2) mặc
định an toàn, ngoại lệ phải xin, có hạn và công khai; (3) quy tắc nào cũng có chỗ kiểm tự động, không dựa vào trí nhớ; (4) chặn
thứ hành động được ngay (lỗ hổng có bản vá), theo dõi phần còn lại; (5) triển khai theo pha để không ai phải tắt gate.

## 2. Image nền được duyệt

| Image | Digest | Dùng cho | Lý do |
| --- | --- | --- | --- |
| `python:3.12.16-slim-trixie` | `sha256:8523d6abeb48ceae0b7240d30c5808fc26cb79c1a635bacdf19cf3baecfbec07` | Stage build của service Python | Có pip, venv, glibc; wheel manylinux chạy được |
| `gcr.io/distroless/python3-debian13:nonroot` | `sha256:1c32c3720dc4c7f0c7dbe998737f32c200add6511eca7cec705008be488b87d6` | Runtime job Python chỉ dùng thư viện chuẩn | Không shell, không pip, UID 65532 sẵn |
| `python:3.12.16-alpine3.24` | `sha256:e6dae589c1c05976188fd3bd019afd091445fc533ed2ea29001beddc7368a9c8` | Công cụ nội bộ nhỏ, không có dependency C | Nhỏ, ít CVE; chỉ khi mọi wheel có bản musllinux |
| `nginx:1.30.6-alpine` | `sha256:0e52bd054126cdc040b1276c0af347aeb02a41b9cfe305d6094767ac30e97949` | Phục vụ frontend tĩnh và reverse proxy | Nhánh stable, ghim theo module 05 |

Image Node.js và Go được thêm theo cùng quy trình khi team tương ứng chốt bản (digest lấy lúc duyệt). Renovate mở PR cập nhật
digest hằng tuần; platform team merge sau khi CI của image mẫu xanh.

## 3. Quy tắc Dockerfile

- Chỉ `FROM` image trong danh sách phần 2, ghim tag kèm digest; cấm `latest` và FROM không tag (hadolint DL3006, DL3007).
- Multi-stage: compiler, header và công cụ build chỉ ở stage build; stage runtime không có `gcc`, `make`, trình quản lý gói.
- `USER` là UID số không phải 0 (ví dụ `10001:10001`), đặt trước `CMD`; mã nguồn thuộc root, app không ghi được vào đó.
- `CMD`/`ENTRYPOINT` dạng exec; script khởi động kết thúc bằng `exec`; app cần dọn tiến trình con thì dùng `tini`.
- Có `HEALTHCHECK` (hoặc liveness/readiness probe khi chạy trên Kubernetes) gọi endpoint không phụ thuộc DB.
- Chép manifest dependency trước mã nguồn để cache hiệu quả; dùng lock file (`uv.lock`, `package-lock.json`, `go.sum`).
- `.dockerignore` dạng allowlist; không `COPY . .` ở stage runtime; không bí mật trong `ARG`/`ENV`, bí mật lúc build qua `RUN --mount=type=secret`.
- Gắn nhãn OCI `org.opencontainers.image.source`, `.revision`, `.version`; CI kiểm bằng `docker buildx imagetools inspect`.
- hadolint và conftest chạy trong CI cho mọi Dockerfile; vi phạm quy tắc trên chặn merge.

## 4. Quét lỗ hổng và thời hạn vá

| Mức độ | Có bản vá | Thời hạn | Gate |
| --- | --- | --- | --- |
| CRITICAL | Có | 7 ngày | Chặn build mới, mở ticket P1 cho image đang chạy |
| HIGH | Có | 30 ngày | Chặn build mới, ticket P2 cho image đang chạy |
| CRITICAL, HIGH | Không | Rà soát hằng tháng | Không chặn, dashboard và VEX khi không bị ảnh hưởng |
| MEDIUM | Có | 90 ngày | Không chặn, gom vào lần rebuild image nền |
| LOW, UNKNOWN | Có hoặc không | Không đặt hạn | Không chặn, chỉ báo cáo |

Gate là trivy với cấu hình chung của tổ chức (`severity: HIGH,CRITICAL`, `ignore-unfixed`, `exit-code: 1`), DB được cache và
cập nhật mỗi 6 giờ trong CI; DB cũ hơn 24 giờ thì job cảnh báo. Image đang chạy được quét lại hằng ngày.

## 5. Ngoại lệ

- Ngoại lệ là mục trong `.trivyignore.yaml` của repo service, khoanh bằng `purls` có phiên bản; không ngoại lệ toàn cục.
- Mỗi mục có `statement` gồm ticket, lý do không khai thác được (bằng chứng: code path, cấu hình), người xác minh, kế hoạch.
- `expired_at` tối đa 90 ngày; hết hạn thì gate đỏ lại và chủ ngoại lệ phải xin gia hạn kèm tiến độ.
- PR thêm ngoại lệ cần một người của security phê duyệt (CODEOWNERS trên `.trivyignore.yaml`).
- Tuyên bố "không bị ảnh hưởng" từ vendor phải ở dạng VEX (OpenVEX hoặc CycloneDX), đưa vào trivy bằng `--vex`.
- Dashboard công khai số ngoại lệ và tuổi trung bình theo team, xem lại trong họp vận hành hằng tháng.

## 6. Registry, tag và chuỗi cung ứng

- Một registry duy nhất cho production, bật tag immutability; mỗi build có tag theo commit SHA và tag phiên bản.
- Manifest deploy tham chiếu image theo digest (`repo@sha256:...`); admission controller từ chối tham chiếu chỉ có tag.
- CI sinh SBOM (CycloneDX) và provenance SLSA bằng BuildKit (`--sbom=true --provenance=mode=max`), đính kèm image.
- Ký image bằng cosign keyless với OIDC của GitHub Actions; admission (Kyverno `verifyImages`) chỉ nhận image đã ký từ đúng workflow.
- Image không được kéo trực tiếp từ Docker Hub ở production: đi qua pull-through cache của registry để tránh rate limit và tag bị xoá.

## 7. Runtime

- `runAsNonRoot: true`, `runAsUser` là UID của image; cấm `privileged` và `hostPath` tới `/var/run/docker.sock`.
- `readOnlyRootFilesystem: true` (read-only rootfs), chỗ ghi tạm là `emptyDir`/tmpfs gắn đúng thư mục cần.
- `allowPrivilegeEscalation: false` (tương đương `no-new-privileges`), `capabilities.drop: [ALL]`, chỉ thêm capability có lý do.
- seccomp `RuntimeDefault`; namespace production gắn Pod Security Standard `restricted` ở chế độ enforce.
- Mọi container có giới hạn CPU và RAM; OOMKilled lặp lại mở ticket cho team sở hữu.

## 8. Triển khai, đo lường và rủi ro

- Tuần 1-4: gate chạy chế độ báo cáo, dashboard theo team; thu hồi và cấp mới khoá API đã lộ trong `.env` ngay tuần 1.
- Tháng 2: chặn build mới với CRITICAL có bản vá, `latest`, `USER` root; 4 service dùng docker.sock có kế hoạch thay thế.
- Quý 2: chặn HIGH có bản vá, admission bắt buộc digest và chữ ký; image cũ chưa đạt có ticket với hạn theo phần 4.
- Metric: tỷ lệ image đạt chính sách theo team, tuổi trung vị của lỗ hổng có bản vá, số ngoại lệ còn hiệu lực, thời gian từ digest image nền mới tới khi mọi service rebuild.
- Rủi ro: team tắt gate khi gấp, giảm bằng đường break-glass có log và review sau sự cố; platform team 3 người thành nút thắt, giảm bằng template Dockerfile và workflow dùng chung.
- Rủi ro: chặn nhầm hotfix lúc sự cố vì CVE mới công bố cùng ngày, giảm bằng ngoại lệ khẩn cấp hết hạn sau 7 ngày.
`````
