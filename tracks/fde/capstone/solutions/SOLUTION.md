# Lời giải tham chiếu capstone: M00–M03

`project/` là repo riêng mẫu của người học (không phải repo git lồng: test M00 chép nó vào thư mục tạm rồi
`git init` + `git add -A` khi `SOLUTION=1`). Nó tự chứa: không import `testkit`/`fdekit`, không trỏ vào repo học; mọi
đầu vào từ repo học (bản phát hành, binary compose) đi qua biến `make`.

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/capstone -q -rs --durations=10
uv run pytest tracks/fde/capstone/solutions/project/tests -q        # test riêng của repo mẫu (preflight)
```

`uv run pytest tracks/fde/capstone` **không** thu thập `solutions/project/tests` (`capstone/conftest.py`); validator
`tests/test_fde_track.py` cũng không quét repo mẫu khi tìm lệnh `docker`/`qemu` trần.

## Cấu trúc repo mẫu

| Tệp | Milestone | Vai trò |
| --- | --- | --- |
| `README.md`, `LICENSE`, `.gitignore`, `Makefile` | M00 | Case study, MIT cho script, chặn khoá/`.env`/tar/CUAD, bốn target |
| `survey/site_survey.sh`, `survey/preflight.py`, `survey/REQUIREMENTS.yaml` | M01 | Survey module 01 + `docker_compose`, `insecure_registries`; preflight + check `compose` |
| `reports/site-survey.md`, `reports/*-lawfirm-staging.json` | M01 | Báo cáo khoảng cách cho IT, kết quả thô đo trên VM 5120 MB |
| `sites/lab.conf`, `sites/lawfirm-staging.conf` | M02–M03 | Registry, bind, cổng theo site |
| `delivery/release.lock`, `fetch_release.sh`, `fetch_compose.sh`, `build_bundle.sh` | M02 | Lấy bản phát hành + compose, kiểm sha, dựng bundle tái lập |
| `delivery/install.sh`, `delivery/verify.sh` | M02–M03 | Installer 9 bước, kiểm tra sau cài |
| `tests/test_preflight.py` | M01 | Test riêng của repo |

## M00

- `.gitignore` chặn `*.pem *.key id_* .env .env.* (trừ .env.example) quillo.env *.tar *.gguf dist/ .cache/ data/ cuad/`.
- `Makefile`: `SSH` là tiền tố lệnh ssh (rỗng = chạy tại chỗ), `REMOTE_BUNDLE` mặc định `bundle` khi có `SSH`. Các biến
  bản phát hành được `export` cho script con. Không có `$(shell …)`, nên `make -n` không chạy gì.

## M01: lawfirm-staging đo thật (2026-11-04)

Survey trên VM 5120 MB: Ubuntu 22.04, kernel 5.15, glibc 2.35, 2 CPU, `MemTotal` 4913 MB, 27,2 GiB trống, không GPU,
không proxy, sudo có, SELinux n/a, Docker, egress none, `docker_compose` null, `insecure_registries` `[]`.
Preflight: không blocker; warning `egress`, `compose`. Với `mem_mb` 2048 (mặc định của hồ sơ) có blocker `mem`
(2048 < 0,9 × 4096), vì vậy test chấm survey ở 5120 MB, cùng RAM mà M03 cài. Báo cáo thêm hai warning không tự động
(`registry`: HTTP chưa có trong `insecure-registries`; `mem`: chỉ đủ cho llm-small) và bốn việc cần IT.

Bộ chấm M01 chống output viết cứng: số đo lấy trong cùng VM; lần chạy hai cài proxy có mật khẩu ngẫu nhiên và một biến
môi trường bí mật, URL phải bị bỏ `user:pass@` và không chuỗi nào lọt ra. Preflight chấm hai bộ facts (5120 → không
blocker, 2048 → blocker `mem`).

## M02: bundle và installer

`make bundle SITE=… BUNDLE_DIR=…`:

1. `fetch_release.sh` chép tar vào thư mục tạm cạnh `BUNDLE_DIR`, tính sha256 **trên bản chép** (không phải bản gốc),
   so với `QUILLO_RELEASE_SHA256` hoặc `release.lock`, kiểm `manifest.json` đúng version.
2. `fetch_compose.sh` lấy `COMPOSE_BIN` hoặc tải về `.cache/`, kiểm sha ghim trên bản chép.
3. Thêm `REQUIREMENTS.yaml` lấy từ trong tar, `install.sh`, `verify.sh`, `site.conf`; chmod cố định; `SHA256SUMS` sắp
   theo `LC_ALL=C`, ghi ra `.partial` rồi đổi tên.
4. Chỉ khi mọi bước xong mới thay `BUNDLE_DIR` (từ chối ghi đè thư mục không rỗng mà không có `SHA256SUMS`). Sai sha ⇒
   thư mục tạm bị xoá, `BUNDLE_DIR` không đổi.

`install.sh` (bash, root) — đường lỗi đã truy:

| Bước | Thay đổi máy | Lỗi thì |
| --- | --- | --- |
| 1 `sha256sum -c SHA256SUMS`, kiểm danh sách bắt buộc | không | dừng, nêu tên tệp `FAILED`; tệp lạ ngoài danh sách chỉ cảnh báo |
| 2 preflight: lệnh, Docker, CPU/RAM (chừa 10%)/đĩa theo `REQUIREMENTS.yaml`, registry `/v2/`, cổng | không (đo `df` ở thư mục cha đang có) | dừng |
| 3 đọc luồng tar, sha từng tệp theo `manifest.json`, chặn đường dẫn lạ/symlink | không | dừng, nêu `sha256 sai <đường dẫn>` |
| 4 giải nén vào `releases/.<bản>.partial`, kiểm lại cây, `mv -T`; bản đã có thì kiểm lại cây | `/opt/quillo/releases` | xoá `.partial` (trap), dừng |
| 5 compose vào `/opt/quillo/bin/docker-compose` (chỉ khi khác) | `/opt/quillo/bin` | dừng |
| 6 `insecure-registries` (chỉ site có registry): ghi nguyên tử, `.bak-quillo`; restart Docker chỉ khi đổi | `daemon.json`, Docker | restart lỗi ⇒ trả `daemon.json` cũ (hoặc xoá nếu trước đó chưa có), restart lại, dừng |
| 7 `docker load` → `tag` → `push` | image, registry | dừng |
| 8 `/etc/quillo/quillo.env` (0600, sinh một lần), `compose.site.yaml` ngoài cây release, `inbox` uid 10001 | `/etc/quillo`, `/opt/quillo/site`, `/opt/quillo/data` | dừng |
| 9 `compose up -d --wait`, `/healthz` | container | in `ps -a`, dừng; **không** tự gỡ (một bản duy nhất; rollback ở M09) |

Mọi lần dừng ghi `failed <lý do>` vào `/var/log/quillo-install.log`; thoát bất ngờ (lệnh lỗi dưới `set -e`) cũng ghi
`failed mã N` qua trap. Chạy lại cùng bản: mọi bước kiểm lại, không gì đổi, compose không tạo lại container.

## M03: chỗ hỏng do khách (chỉ ghi ở đây)

Installer tập trên `lab-open` chạy êm; trên `lawfirm-staging` có bốn chỗ hỏng thật do hồ sơ khách:

| Triệu chứng | Nguyên nhân | Xử lý trong installer |
| --- | --- | --- |
| `docker: unknown command: docker compose` | Docker gói Ubuntu, không plugin compose, không mạng để cài | Binary compose ghim trong bundle, gọi trực tiếp ở `/opt/quillo/bin` |
| `http: server gave HTTP response to HTTPS client` khi push | Registry HTTP chưa trong `insecure-registries` | Bước 6; cảnh báo vì `live-restore` tắt ⇒ restart dừng mọi container |
| Mọi thứ healthy trong VM, `/healthz` từ ngoài timeout | `compose.yaml` mặc định bind `127.0.0.1` | `QUILLO_BIND=0.0.0.0` từ `site.conf` |
| `worker` lỗi quyền ghi `/data/inbox` | Image chạy uid 10001, thư mục bind thuộc root | `install -d -o 10001 -g 10001` |

Hai lớp kiểm toàn vẹn: `SHA256SUMS` bắt byte hỏng trong tar (thông báo `quillo-1.0.0.tar`); khi `SHA256SUMS` bị viết
lại, bước 3 (đọc luồng, chưa ghi ra đĩa) bắt tệp sai trong tar (thông báo `models/qwen2.5-0.5b-instruct-q4_k_m.gguf`).
Cả hai lần máy không có image, container, `daemon.json` hay restart Docker. Cả hai lớp vẫn nằm trong bundle; xác thực
nguồn gốc cần sha của `SHA256SUMS` gửi qua kênh riêng (`build_bundle.sh` in ra) hoặc ký.

## Thời gian đo (2026-11-04, laptop 16 core, NVMe, máy đang chạy việc khác)

| Test | Thời gian |
| --- | --- |
| `test_m00_layout`, `test_m00_standalone`, `test_m00_no_secrets_committed` | < 0,1 s mỗi test |
| `test_m01_survey_matches_lawfirm` (boot 5120 MB, survey ×2, preflight) | 56 s |
| `test_m01_preflight_report` | 0,1 s |
| `test_m02_bundle_reproducible` (3 lần dựng bundle 1,1 GB) | 7,5 s |
| `test_m02_installer_idempotent` (bundle 2,3 s, boot + chép 14,7 s, cài 64,2 s, cài lại 15,4 s) | 100 s |
| `test_m03_rejects_tampered_bundle` (bundle 2,1 s, boot + chép 18,3 s, hai lần từ chối 4,9 s và 5,9 s) | 39 s |
| `test_m03_airgapped_install` (cài 68,1 s, verify ×2) | 70 s |

Ba VM boot nối tiếp (không bao giờ hai VM cùng lúc), mỗi VM 5120 MB. Hai test M03 dùng chung một máy (fixture
`module`, dựng lười trong test đầu cần nó để lỗi dựng là FAIL chứ không phải ERROR).

## Lỗi hay gặp

- Kiểm `SHA256SUMS` rồi giải nén thẳng vào `/opt` trước khi kiểm `manifest.json`: bundle bị sửa đã nằm trên đĩa khách.
- Sửa `compose.yaml` trong cây release bằng `sed`: cây không còn khớp manifest, lần chạy lại tưởng bản bị sửa.
- Cài plugin compose vào `/usr/local/lib/docker/cli-plugins`: đổi hành vi `docker` của mọi người dùng khác trên máy IT quản.
- `make bundle` ghi thẳng vào `BUNDLE_DIR` rồi lỗi giữa chừng: còn lại một bundle thiếu tệp mà vẫn có tên hợp lệ.
- `verify.sh` chỉ `curl /healthz`: báo đạt khi `worker` đã chết (không ai nạp tài liệu mới).
- `verify.sh` đọc cột Status của `docker ps`: container `Restarting` vẫn nằm trong `docker ps`, `worker` không có
  healthcheck nên không bao giờ `unhealthy`; lời giải kiểm `.State.Status == running` bằng `docker inspect` cho từng dịch vụ.
