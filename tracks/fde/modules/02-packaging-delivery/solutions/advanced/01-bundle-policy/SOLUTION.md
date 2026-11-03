# Lời giải: Định dạng bundle và chính sách version cho ba khách

## Hướng làm

1. **Tìm ba "cực"**: kênh hẹp nhất (bệnh viện, ~2 MB/s, đĩa 8 GB), quy trình chậm nhất (ngân hàng: 2 GB/tệp, duyệt 5 ngày
   cho mỗi thành phần mới, nâng mỗi quý, rollback trong cửa sổ), nhịp nhanh nhất (công ty luật: hằng tháng, có staging).
2. **Phân thứ trong bundle theo tần suất đổi và người phải duyệt lại**: model và image nền đổi vài lần một năm và mỗi lần
   đổi là một lượt duyệt ở ngân hàng; mã ứng dụng đổi hằng tháng. Từ đó ra hai lớp.
3. **Viết trạng thái database sau từng bản** trong lộ trình rồi hỏi "bản trước chạy được không": 1.1, 1.2 chỉ thêm cột có
   `DEFAULT` ⇒ được; 2.0 bỏ cột ⇒ không. Đó là toàn bộ hợp đồng version.
4. **Tính mọi con số** từ bảng đề, ghi phép tính ngay cạnh.

## Rubric (tự chấm, đạt đủ 10 mục)

| # | Bài mẫu đạt ở đâu |
| --- | --- |
| B1 | Mục 1.1–1.2: một định dạng, cây thư mục, bảng trường manifest (tên, version, platform, files sha256+size, images+digest, schema `from`/`to`) |
| B2 | Mục 1.3: lớp nền 1 102 MB (1 702 MB với `llm-medium`), lớp ứng dụng ~60 MB; mọi tệp ≤1 900 MB, tệp lớn hơn thì `split` có sha256 từng phần |
| B3 | Mục 4.2: cùng `images/*.tar`; compose v2 binary trong lớp nền cho bệnh viện/công ty luật; ngân hàng dùng Quadlet (`~/.config/containers/systemd/`) + `loginctl enable-linger` do IT làm một lần; volume nhãn `:Z` |
| B4 | Mục 2.1: bảng PATCH/MINOR/MAJOR theo migration + quay lại; 1.1.0, 1.2.0 = MINOR, 2.0.0 = MAJOR |
| B5 | Mục 2.2: chuỗi migration liên tục, CI kiểm đúng các đường nhảy N−3→N; ngân hàng không cần bản trung gian trong cùng MAJOR, nhưng **phải** qua 1.3 trước 2.0 |
| B6 | Mục 2.3: hỗ trợ N, N−1; ngân hàng một bản "dài hạn" 6 tháng; bản vá khẩn là PATCH đầy đủ lớp ứng dụng, qua cùng manifest, chữ ký, preflight |
| B7 | Mục 3: bảng rollback có thời gian; 2.0 tách expand (1.3, embed lại nền theo lô trong giờ làm việc) và contract (2.0, ~20 phút trong cửa sổ) |
| B8 | Mục 4.3: mỗi khách ≥2 khác biệt cụ thể (proxy+CA, đĩa, registry, staging/prod, Podman/SELinux, không sudo) trong hồ sơ ngoài bundle |
| B9 | Mục 5: sha256 qua kênh riêng, cosign khoá (kiểm offline, tắt tlog), khoá công khai giao một lần kèm fingerprint, SBOM CycloneDX mỗi lớp |
| B10 | Mục 4.1: bảng kênh, kích thước, thời gian truyền (60 MB / 2 MB/s ≈ 30 s; 1 102 MB ≈ 9 phút), tần suất, người cài; công ty luật: staging nhận trước, prod cài đúng bundle đã soak (cùng sha256) |

Lỗi hay gặp khi tự chấm: "bundle riêng cho ngân hàng" (trượt B1: hai bản build là hai bản phải test); "MAJOR khi có tính
năng lớn" (trượt B4: khách cần biết quay lại được không, không cần biết tính năng lớn cỡ nào); quên rằng **mỗi image hay
binary mới** ở ngân hàng là 5 ngày duyệt (B2/B10: đó là lý do lớp nền phải ít đổi).

## Bài mẫu

```markdown
# Chính sách đóng gói và version của quillo cho khách triển khai tại chỗ

Người viết: FDE · Ngày: 04/11/2026 · Người đọc: trưởng nhóm sản phẩm quillo

## 1. Định dạng bundle

### 1.1 Một định dạng cho mọi khách

Mọi khách nhận cùng một bản build. Khác biệt giữa khách nằm ở hồ sơ cấu hình ngoài bundle (mục 4.3), không ở bản build:
mỗi bản build riêng là một bản phải test, vá và ký riêng.

    quillo-app-1.2.0-linux-amd64.tar          lớp ứng dụng, đổi hằng tháng
      quillo-app-1.2.0/
        manifest.json                          đầu tar
        images/quillo-api.tar
        compose.yaml  quadlet/*.container      hai cách khởi chạy (mục 4.2)
        migrations/0001…0003_*.sql
        install.sh  preflight.sh  REQUIREMENTS.yaml  .env.example  LICENSE  sbom/app.cdx.json
    quillo-base-2026.1-linux-amd64.tar        lớp nền, đổi vài lần một năm
      quillo-base-2026.1/
        manifest.json
        images/pgvector.tar  images/llama-cpp-server.tar
        models/qwen2.5-0.5b-instruct-q4_k_m.gguf  models/nomic-embed-text-v1.5.Q8_0.gguf
        tools/docker-compose-v2  (binary tĩnh, ghim sha256)
        sbom/base.cdx.json

### 1.2 Trường của manifest

| Trường | Ví dụ | Dùng để |
| --- | --- | --- |
| `name`, `version`, `layer` | `quillo`, `1.2.0`, `app` | Installer từ chối nhầm sản phẩm/lớp |
| `platform` | `linux/amd64` | Preflight so với `uname -m` |
| `requires.base` | `>=2026.1,<2027.0` | Lớp ứng dụng đòi lớp nền tương thích |
| `requires.os`, `requires.runtime` | `ubuntu>=20.04` hoặc `rocky>=8`; `docker>=24` hoặc `podman>=4.6` | Preflight |
| `schema` | `{"from": ["0001","0002"], "to": "0003"}` | Bản này nâng được từ schema nào |
| `files` | `{đường dẫn: {"sha256", "size"}}` | Kiểm toàn vẹn, tính chỗ trống trước khi giải nén |
| `images` | `pgvector/pgvector:0.8.6-pg16@sha256:ccc6…` | Digest gốc của từng image |

### 1.3 Hai lớp và kích thước

| Lớp | Thành phần | Kích thước | Đổi khi |
| --- | --- | --- | --- |
| Nền | pgvector 156 + llama.cpp 309 + llm-small 491 + embed 146 | **1 102 MB** (1 702 MB nếu dùng llm-medium: +600) | Đổi model, nâng Postgres/llama.cpp: 2–3 lần/năm |
| Ứng dụng | quillo-api 59 MB + compose, quadlet, migration, script | **~60 MB** | Mỗi tháng |

Mọi tệp trong bộ giao ≤1 900 MB. Lớp nền với llm-medium (1 702 MB) vẫn dưới ngưỡng; lớp nào vượt thì `split -b 1900M`,
manifest ngoài ghi sha256 từng phần **và** tệp ghép, installer ghép rồi kiểm trước khi giải nén.

## 2. Hợp đồng version

### 2.1 Ý nghĩa số version

| Loại | Database | Quay lại bản trước | Lộ trình |
| --- | --- | --- | --- |
| PATCH `x.y.Z` | Không migration | Đổi `current`, khởi động lại | Bản vá |
| MINOR `x.Y.0` | Chỉ **thêm** (cột có `DEFAULT`, bảng, index) | Được: bản trước chạy được trên schema mới | 1.1.0 (`tags`), 1.2.0 (`tenant_id`) |
| MAJOR `X.0.0` | Có bỏ/đổi (cột, định dạng dữ liệu) | Chỉ bằng khôi phục backup | 2.0.0 (bỏ embedding cũ) |

### 2.2 Đường nâng cấp

Migration đánh số liên tục, mỗi bản chạy được chuỗi từ bất kỳ schema nào trong `schema.from`. CI kiểm mọi đường nhảy
N−3→N (nâng quý của ngân hàng là nhảy 3 MINOR) trên dữ liệu mẫu, kể cả đường quay lại N−1. Trong cùng MAJOR không cần bản
trung gian. Qua MAJOR thì **bắt buộc** qua MINOR cuối (1.3) trước, vì 1.3 làm phần "expand" của 2.0 (mục 3).

### 2.3 Hỗ trợ và vá khẩn

Hỗ trợ N và N−1 MINOR. Ngân hàng chọn một bản "dài hạn" mỗi quý, được vá bảo mật 6 tháng. Bản vá khẩn là một PATCH đầy
đủ của lớp ứng dụng (~60 MB), cùng manifest, chữ ký, preflight, installer; không bao giờ chép tay một tệp `.py` lên máy
khách. Lớp nền không đổi nên ngân hàng không phải duyệt lại image hay model.

## 3. Rollback

| Bản | Quay lại bằng | Thời gian ước tính |
| --- | --- | --- |
| PATCH, MINOR | Installer trỏ `current` về release trước, khởi động lại; schema giữ nguyên | ~2 phút (ước tính; đo lại trên staging công ty luật) |
| Đổi lớp nền | Release ứng dụng trước + image nền trước (installer giữ lớp nền N−1 trên đĩa nếu đủ chỗ) | ~5 phút |
| MAJOR | Khôi phục `pg_dump` lấy ngay trước migration + release trước | Theo dung lượng DB; đo trên staging trước mỗi lần nâng |

2.0.0 tách hai bước để vừa cửa sổ 4 giờ của ngân hàng: **1.3** (MINOR, quý 1/2027) mang model embedding mới trong lớp
nền mới, thêm cột embedding mới và một tác vụ nền embed lại theo lô ngoài giờ cao điểm (3 giờ CPU cho 100 000 trang, chia
nhiều đêm, không cần cửa sổ); bản 1.3 vẫn đọc cột cũ. **2.0** (MAJOR) chỉ chuyển sang đọc cột mới và bỏ cột cũ: backup +
migration + kiểm ~20 phút, rollback bằng backup nằm gọn trong cửa sổ. Khách nào chưa embed lại xong thì installer 2.0
dừng ở preflight.

## 4. Theo từng khách

### 4.1 Giao hàng

| | Bệnh viện Sông Hồng | Ngân hàng Hải Đăng | Công ty Luật Minh Tâm |
| --- | --- | --- | --- |
| Kênh | SFTP qua VPN | MFT (≤2 GB/tệp, quét mã độc) | USB mã hoá do FDE mang tới |
| Cập nhật thường kỳ | Lớp ứng dụng 60 MB ≈ 30 s ở 2 MB/s | Lớp ứng dụng 60 MB, mỗi quý | Lớp ứng dụng 60 MB, mỗi tháng |
| Đổi lớp nền | 1 102 MB ≈ 9 phút ở 2 MB/s, chép trước cửa sổ | 1 702 MB (llm-medium), 1 tệp; duyệt 5 ngày làm việc ⇒ nộp trước cửa sổ ≥2 tuần | 1 102 MB cùng USB |
| Ai cài | FDE qua VPN trong cửa sổ thứ Năm, IT ngồi cùng | IT ngân hàng chạy theo runbook, FDE trực qua điện thoại | FDE tại chỗ, staging trước |
| Ghi chú | Chép bundle vào máy **trước** cửa sổ; xoá tar sau khi nạp | Bộ giao gồm SBOM + chữ ký cho An ninh thông tin | Prod chỉ nhận đúng bundle đã chạy staging 2 tuần (so sha256) |

### 4.2 Khởi chạy

Cùng `images/*.tar`: `docker load` và `podman load` đọc cùng định dạng. Bệnh viện và công ty luật dùng binary
`docker-compose-v2` trong lớp nền (đặt vào `~/.docker/cli-plugins/`, không cần mạng). Ngân hàng dùng tệp Quadlet
(`~/.config/containers/systemd/quillo-*.container`) cho Podman rootless: systemd user quản lý container, không cần sudo;
IT chạy `loginctl enable-linger <tài khoản dịch vụ>` một lần để dịch vụ sống sau khi đăng xuất. SELinux enforcing: mọi
volume gắn nhãn `:Z`, không bao giờ đề nghị tắt SELinux.

### 4.3 Cấu hình riêng (hồ sơ khách trong repo triển khai, ngoài bundle)

- Bệnh viện: proxy `http_proxy` + CA nội bộ cho kiểm tra cập nhật (sản phẩm chạy không cần mạng); đĩa 8 GB ⇒ preflight
  đòi chỗ trống theo manifest, installer giải nén cạnh chỗ cài và xoá tar sau khi nạp; nhắc IT nới đĩa trước lần đổi lớp nền.
- Ngân hàng: Podman rootless + Quadlet, đường dẫn dữ liệu trong home tài khoản dịch vụ, `QUILLO_BIND` là IP nội bộ do IT
  cấp, `llm-medium` (64 GB RAM).
- Công ty luật: tên registry nội bộ cho từng môi trường, hai tệp hồ sơ staging/prod chỉ khác cổng và đường dẫn dữ liệu.

## 5. Toàn vẹn và nguồn gốc

sha256 của từng tệp giao gửi qua kênh khác kênh giao tệp (email từ địa chỉ công ty tới người đã thống nhất). Mọi tệp
giao ký bằng cosign với khoá của công ty (`sign-blob` tắt transparency log vì khách không có mạng), khách kiểm offline
bằng `cosign verify-blob --key cosign.pub`. Khoá công khai giao **một lần** khi ký hợp đồng, kèm fingerprint đọc qua điện
thoại; khoá riêng chỉ nằm trong máy ký của đội phát hành, xoay mỗi năm. Mỗi lớp mang SBOM CycloneDX (syft cho image,
`uv export --format cyclonedx1.5` cho Python) để ngân hàng tự quét lỗ hổng.
```
