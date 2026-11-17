# Lời giải: thiết kế cài quillo không container

## Hướng làm

1. Đọc `compose.yaml` và `Dockerfile` như đặc tả: mỗi dịch vụ chạy chương trình gì, lệnh gì, user nào, cổng nào, đọc
   biến nào, mount gì, healthcheck gì. Ánh xạ từng dòng sang unit `systemd --user`; dòng nào không có tương đương thì ghi
   rõ là **mất** (phần R7).
2. Đi theo từng thành phần của bundle và hỏi "chạy được trên máy **đích** không": Python (Rocky 8 không có 3.12), wheel
   (glibc 2.28), llama.cpp (binary phát hành dựng trên Ubuntu mới, glibc cao hơn 2.28; tập lệnh CPU), model (không phụ
   thuộc máy).
3. Đi qua mọi "tật" của máy (module này): linger, `/tmp` noexec, `nofile`, SELinux, cổng, không sudo.
4. Postgres không phải của bạn: tách rõ việc của DBA, TLS kiểm chứng chỉ, mật khẩu không nằm trong URL.
5. Kết luận cho product: hỗ trợ có điều kiện, ai trả chi phí bảo trì.

Chỗ hay sai: dùng binary llama.cpp phát hành sẵn (chạy trên Ubuntu 22.04 của bạn, trên Rocky 8 báo `GLIBC_2.3x not
found`); tạo venv bằng `platform-python` 3.6; mật khẩu DB trong `ExecStart=` hay trong URL ở `Environment=` (hiện trong
`systemctl --user show`); bỏ qua linger; quên `QUILLO_MIGRATIONS_DIR` (ngoài image, đường dẫn mặc định là cây mã nguồn);
mở cổng llm/embed ra mạng; quên rằng mất `read_only`/`no-new-privileges`/quét image là mất thật, không phải chi tiết.

## Rubric (tự chấm, đạt đủ 8 mục)

| # | Bài mẫu đạt ở đâu |
| --- | --- |
| R1 | Mục 1: bảng 5 dòng, `db` thành Postgres của DBA, lệnh `llama-server`/`uvicorn`/`python -m quillo.ingest` lấy đúng từ `compose.yaml`/`Dockerfile`, cổng 18081/18082 chỉ `127.0.0.1`, api ở `10.20.30.41:18080` cho reverse proxy |
| R2 | Mục 2: 6 thành phần, mỗi thứ phiên bản + sha256 + điều kiện (glibc 2.17/2.28, AVX2, Python 3.12), kiểm bằng `preflight.sh` trước khi đụng gì |
| R3 | Mục 3: cây thư mục, 4 unit user có `After=`/`Requires=`, `Restart=on-failure`, `MemoryMax` ghi rõ không áp được trên cgroup v1, secret trong `~/.pgpass` và `quillo.env` 0600 |
| R4 | Mục 4: linger (xin IT, lệnh kiểm), `TMPDIR`, `nofile` 4096 đủ và vì sao, SELinux `unconfined_t` + câu hỏi `id -Z`/`user_exec_content`, mọi cổng ≥ 1024 |
| R5 | Mục 5: URL không mật khẩu + `~/.pgpass`, `sslmode=verify-full` + `sslrootcert`, quyền xin DBA, backup là việc của DBA kèm điều kiện trước nâng cấp |
| R6 | Mục 6: thứ tự worker → api → (migration lúc api khởi động) → kiểm, điểm không quay lại là migration, rollback bằng `current` cũ + DB tương thích ngược hoặc restore |
| R7 | Mục 7: bảng mất/được, chi phí vá runtime và llama.cpp, đề xuất "hỗ trợ có điều kiện" với 4 điều kiện |
| R8 | Mục 7: 5 việc xin IT/DBA kèm lệnh kiểm, 5 câu hỏi mở |

---

## Bài mẫu

# Kế hoạch cài quillo 1.1.0 không container: Ngân hàng — phòng pháp chế

Gửi: product, IT hạ tầng, DBA · Từ: FDE … · Ngày: 11/11/2026

## Tóm tắt

- Chạy `quillo` 1.1.0 trên `app-legal-01` (Rocky 8.10) **không** container: Python 3.12 mang theo, wheelhouse đúng
  `requirements.lock`, `llama-server` dựng cho Rocky 8, 4 unit `systemd --user` của `svc-quillo`, tất cả trong `$HOME`.
- Postgres là của DBA (`db01.bank.internal`), kết nối TLS kiểm chứng chỉ; không có Postgres trên máy app.
- Xin IT 3 việc (linger, mở cổng 18080 từ reverse proxy, xác nhận nhãn SELinux của user), DBA 2 việc (quyền, backup).
- Rủi ro chính: mất cô lập của container; FDE/product phải tự vá Python và llama.cpp.
- Đề xuất cho product: hỗ trợ có điều kiện cho khách "không container", không phải đường mặc định.

## 1. Ánh xạ dịch vụ

| Compose | Không container | Phiên bản | Lệnh (từ `compose.yaml`/`Dockerfile`) | User | Thư mục | Cổng |
| --- | --- | --- | --- | --- | --- | --- |
| `db` (`pgvector/pgvector:0.8.6-pg16`) | Postgres 16 của DBA | 16.x, `vector` 0.8 | — | DBA | — | `db01.bank.internal:5432` (TLS) |
| `llm` | `quillo-llm.service` | llama.cpp `b11718` | `llama-server -m <models>/qwen2.5-0.5b-instruct-q4_k_m.gguf --alias llm-small -c 4096 -t 2 --host 127.0.0.1 --port 18081` | `svc-quillo` | `~/quillo/current/bin`, `~/quillo/models` | `127.0.0.1:18081` |
| `embed` | `quillo-embed.service` | llama.cpp `b11718` | `llama-server -m <models>/nomic-embed-text-v1.5.Q8_0.gguf --embeddings --pooling mean -c 2048 -b 2048 -ub 2048 -t 2 --host 127.0.0.1 --port 18082` | `svc-quillo` | như trên | `127.0.0.1:18082` |
| `api` | `quillo-api.service` | quillo 1.1.0 | `uvicorn quillo.app:create_app --factory --host 10.20.30.41 --port 18080 --no-access-log` | `svc-quillo` | `~/quillo/current/venv` | `10.20.30.41:18080` (chỉ reverse proxy gọi tới) |
| `worker` | `quillo-worker.service` | quillo 1.1.0 | `python -m quillo.ingest --watch ~/quillo/data/inbox` | `svc-quillo` | `~/quillo/data/inbox` (`done/`, `failed/`) | — |

`QUILLO_LLM_URL=http://127.0.0.1:18081`, `QUILLO_EMBED_URL=http://127.0.0.1:18082`, `QUILLO_VERSION=1.1.0`,
`QUILLO_MIGRATIONS_DIR=~/quillo/current/migrations` (ngoài image, đường mặc định trỏ vào cây mã nguồn nên phải đặt).

## 2. Bundle

| Thành phần | Nguồn | Ghim | Điều kiện trên máy đích | Kiểm trước khi cài |
| --- | --- | --- | --- | --- |
| CPython 3.12 standalone (`install_only_stripped`) | python-build-standalone `20261021` | 3.12.15 + sha256 (như bài intermediate 02) | glibc ≥ 2.17 (máy có 2.28) | `python3 -V` sau khi giải nén vào thư mục stage |
| Wheelhouse quillo | `requirements.lock` của sản phẩm + wheel `quillo-1.1.0` dựng từ cây mã | Hash của lockfile (`--require-hashes`) | Wheel `cp312` thẻ `manylinux_2_28` trở xuống (cryptography, psycopg-binary, pydantic-core có sẵn); không sdist | `pip install --no-index --require-hashes` vào venv stage |
| `llama-server` | Mã nguồn tag `b11718`, dựng trong container `rockylinux:8` ở văn phòng (`gcc-toolset`), `-DGGML_NATIVE=OFF -DGGML_CPU_ALL_VARIANTS=ON -DGGML_BACKEND_DL=ON` để chọn biến thể theo CPU lúc chạy | sha256 của từng tệp trong `bin/` | glibc ≤ 2.28 khi dựng; CPU x86-64 bất kỳ (biến thể AVX2/AVX-512 tự chọn) | `llama-server --version`, `objdump -T` không đòi `GLIBC_` > 2.28 |
| Model GGUF | `fdekit.MODELS` (`llm-small`, `embed-small`) | sha256 đã ghim | — | `sha256sum -c` |
| Migration | `migrations/` của bản 1.1.0 | Trong manifest | — | Manifest |
| Unit + `install.sh` + `preflight.sh` | Bundle | Trong manifest | systemd ≥ 239 | `systemd-analyze --user verify` |

Binary llama.cpp phát hành sẵn (`llama-b11718-bin-ubuntu-x64.zip`) dựng trên Ubuntu mới: không dùng được trên Rocky 8.
Toàn bộ bundle có `SHA256SUMS` + sha của chính nó gửi qua kênh khác như module 03.

## 3. Bố cục cài và unit `systemd --user`

```
/home/svc-quillo/
  quillo/releases/1.1.0/{python,venv,bin,migrations}
  quillo/current -> releases/1.1.0
  quillo/models/*.gguf
  quillo/data/inbox/{done,failed}
  .config/quillo/quillo.env      (0600)
  .config/quillo/bank-ca.pem
  .pgpass                        (0600)
  .config/systemd/user/quillo-{llm,embed,api,worker}.service
```

- Mỗi bản một thư mục trong `releases/`, dựng xong mới đổi `current`.
- `quillo-llm`, `quillo-embed`: `Restart=on-failure`, `RestartSec=5`. `quillo-api`: `Requires=`/`After=` llm và embed,
  `EnvironmentFile=%h/.config/quillo/quillo.env`, `Restart=on-failure`; khởi động chạy migration (khoá advisory, idempotent).
  `quillo-worker`: `After=quillo-api` (để migration xong trước), cùng `EnvironmentFile`.
- `[Install] WantedBy=default.target`. Healthcheck của compose thay bằng `ExecStartPost=` gọi `/health` của llama.cpp
  (chờ tối đa 120 s) để `After=` thật sự nghĩa là "sẵn sàng".
- Giới hạn: `MemoryMax=`/`CPUQuota=` trong unit user **không** có tác dụng trên cgroup v1 của Rocky 8 (không delegation);
  ghi rõ cho IT, theo dõi bằng giám sát của họ. `LimitNOFILE=` chỉ hạ được.
- Secret: `QUILLO_ADMIN_TOKEN` trong `quillo.env` (0600), mật khẩu DB trong `~/.pgpass` (0600, libpq trong
  `psycopg-binary` tự đọc); không secret nào trên `ExecStart=` hay trong `Environment=` của unit (hiện trong
  `systemctl --user show`).

## 4. Máy bị khoá

| Tật | Ảnh hưởng | Xử lý |
| --- | --- | --- |
| Linger tắt | Dịch vụ chết khi phiên cuối của `svc-quillo` đóng | Xin IT `loginctl enable-linger svc-quillo`; kiểm `loginctl show-user svc-quillo -p Linger` = `yes` |
| `/tmp` noexec | Không gì trong stack **chạy** chương trình từ `/tmp`; upload của FastAPI ghi tệp tạm (dữ liệu) vẫn được. Installer không giải nén công cụ vào `/tmp` | Stage trong `~/quillo/releases/.stage-*`; `TMPDIR=%h/quillo/tmp` trong unit để tệp tạm không đầy tmpfs nhỏ |
| `nofile` 4096 | uvicorn + 3 luồng + 2 kết nối llama.cpp + pool Postgres: dưới vài trăm fd | Đủ; preflight in `ulimit -n` và cảnh báo nếu < 1024 |
| SELinux enforcing | Unit user chạy trong domain của user (`unconfined_t` nếu `svc-quillo` map `unconfined_u`): chạy binary trong home, nghe cổng ≥ 1024, kết nối Postgres đều được | Hỏi IT `id -Z` của `svc-quillo`; nếu là user bị giới hạn (`user_u`) thì chạy chương trình trong home cần boolean `user_exec_content` = on, và kết nối mạng ra có thể bị chặn: xin IT trước |
| Cổng | Không root: chỉ ≥ 1024 | 18080 cho api; reverse proxy giữ 443 |

## 5. Postgres của DBA

- `QUILLO_DATABASE_URL=postgresql://quillo@db01.bank.internal:5432/quillo?sslmode=verify-full&sslrootcert=/home/svc-quillo/.config/quillo/bank-ca.pem`;
  mật khẩu trong `~/.pgpass` (`db01.bank.internal:5432:quillo:quillo:<mật khẩu>`). Fingerprint CA đọc lại với An ninh qua
  điện thoại.
- Quyền xin DBA: owner schema `public` của database `quillo` (migration tạo bảng, index HNSW, `ALTER TABLE`); extension
  `vector` cài sẵn (migration chỉ `CREATE EXTENSION IF NOT EXISTS`, không cần superuser khi đã có).
- Backup: DBA (chính sách của họ). Trước mỗi nâng cấp có migration: xin DBA một bản dump/snapshot và thời điểm xác nhận.

## 6. Nâng cấp và rollback

1. Preflight + kiểm bundle mới; dựng `releases/<bản mới>` đầy đủ (venv, binary) khi dịch vụ cũ vẫn chạy.
2. DBA xác nhận backup. Dừng `quillo-worker` rồi `quillo-api` (llm/embed giữ nếu model không đổi).
3. Đổi `current` (nguyên tử), khởi động `quillo-api`: migration chạy. **Điểm không quay lại**: migration đã commit.
4. Kiểm `/healthz` (version mới), hỏi thử một câu có trích dẫn; khởi động worker.
5. Rollback: trước bước 3, chỉ cần không đổi `current`. Sau bước 3: đổi `current` về bản cũ nếu schema mới tương thích
   ngược (1.0.0 chạy được trên schema 1.1.0, cột `tags` có `DEFAULT`); không tương thích thì DBA restore bản backup bước 2.

## 7. So với compose, đề xuất, việc xin IT/DBA, câu hỏi mở

| | Compose (mặc định) | Không container |
| --- | --- | --- |
| Cô lập | Filesystem `read_only`, `tmpfs`, `no-new-privileges`, user 10001, mạng riêng giữa dịch vụ | Mọi tiến trình cùng user, thấy cùng home; mất `read_only`/`no-new-privileges` (thay một phần bằng `NoNewPrivileges=yes`, `ProtectSystem=` chỉ hiệu lực khi user manager hỗ trợ) |
| Chuỗi cung ứng | Image ghim digest, đã quét | Tự dựng llama.cpp, tự gom wheel: phải tự quét (SBOM của wheelhouse, binary) |
| Vá | Image mới | Product phát hành runtime Python + llama.cpp riêng cho Rocky 8 mỗi khi có CVE |
| Được | — | Khớp chính sách ngân hàng, không runtime container, IT quen `systemd` |

**Đề xuất cho product:** hỗ trợ "không container" **có điều kiện**: (1) chỉ trên RHEL/Rocky 8–9 x86-64, (2) Postgres do
khách cấp, (3) product dựng và phát hành `llama-server` + wheelhouse cho đúng nền đó trong pipeline release, (4) khách
chấp nhận bằng văn bản phần mất cô lập. Không làm thành đường mặc định.

**Xin IT/DBA:**

| # | Ai | Việc | Kiểm |
| --- | --- | --- | --- |
| 1 | IT | `loginctl enable-linger svc-quillo` | `loginctl show-user svc-quillo -p Linger` = `Linger=yes` |
| 2 | IT | Mở firewall `reverse-proxy-01` → `10.20.30.41:18080/tcp` | `curl -v http://10.20.30.41:18080/healthz` từ reverse proxy |
| 3 | IT | Xác nhận nhãn SELinux của `svc-quillo` (`id -Z`) và boolean `user_exec_content` nếu user bị giới hạn | `getsebool user_exec_content` |
| 4 | DBA | Database `quillo`, user `quillo` owner schema `public`, extension `vector` 0.8, TLS | `psql "…sslmode=verify-full" -c 'select extversion from pg_extension where extname = $$vector$$'` |
| 5 | DBA | Backup theo chính sách, snapshot trước mỗi nâng cấp | Biên bản thời điểm backup |

**Câu hỏi mở:** (1) `$HOME` của `svc-quillo` nằm trên đĩa local hay NFS? (2) CPU của `app-legal-01` (`lscpu`), có AVX2
không, bao nhiêu lõi thật? (3) Có giám sát nào đọc được `/metrics` không, hay chỉ log? (4) Cửa sổ bảo trì cho nâng cấp?
(5) Ai được đăng nhập bằng `svc-quillo` để trực sự cố (SSH key, ghi log phiên)?
