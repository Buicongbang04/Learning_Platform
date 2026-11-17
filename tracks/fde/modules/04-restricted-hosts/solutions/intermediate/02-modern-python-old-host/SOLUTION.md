# Lời giải: app Python 3.12 trên máy bệnh viện cũ

Lời giải ở `build_bundle.sh` và `install.sh` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/intermediate/02-modern-python-old-host -q
```

Đo 2026-11-11 trên máy của repo: 29 s cả bài (gồm build bundle có tải wheel, boot VM, hai lần cài).

## Máy bệnh viện thật sự có gì

Đo trên `hospital` (golden 2026-11-04):

| Thử | Kết quả |
| --- | --- |
| `python3 -V` | `Python 3.8.10` (hết hỗ trợ từ 10/2024) |
| `python3 -m venv ~/v` | Tạo được thư mục nhưng dừng ở `ensurepip`: gói `python3-venv` không được cài (`No module named 'ensurepip'`); không có `pip` trong venv |
| `pip3` | Không có lệnh |
| Chạy `census` bằng 3.8 | Không tới được: wheel đòi `>=3.12`; ép cài thì `type WardCounts = ...` là `SyntaxError` |
| Mạng | `/etc/environment` đặt `http(s)_proxy=http://10.0.2.100:3128`, nhưng máy chủ này không được ra ngoài: mọi lệnh tải gói treo tới timeout |
| glibc | 2.31: wheel nào chỉ có thẻ `manylinux_2_34`/`2_35` (dựng trên máy mới) sẽ không cài được |

Cài gói hệ thống (`python3.12` từ deadsnakes, `python3-venv`) cần root, mạng và một PPA mà IT bệnh viện sẽ không duyệt
cho máy chủ. Đường còn lại là mang runtime của riêng app.

## Cách làm

**`build_bundle.sh` (máy bạn):**

1. Kiểm sha256 của tarball python-build-standalone đã ghim (`6d752113…`) trước khi chép vào bundle; tệp sai là dừng.
   Bản `install_only_stripped` (~34 MB nén): đủ `bin/python3`, thư viện chuẩn, `venv`, `ensurepip`/`pip`; dựng trên glibc
   2.17 nên chạy được trên Ubuntu 20.04 (2.31) lẫn Rocky 8 (2.28).
2. `uv export --frozen --format requirements.txt` (có hash) + `uv build --wheel` cho app.
3. `pip download` (pip ghim, chạy qua `uvx`) với `--python-version 3.12 --abi cp312 --implementation cp` và các thẻ
   `manylinux_2_31` trở xuống: wheel khớp **máy đích**, không phải máy bạn (máy bạn glibc mới hơn, `uv`/`pip` mặc định chọn
   thẻ mới nhất có thể). `--require-hashes` để wheel phải đúng hash trong lockfile.
4. `SHA256SUMS` cho mọi tệp của bundle.

**`install.sh` (máy khách, user `fde`):**

1. `sha256sum --strict -c SHA256SUMS` trước mọi thay đổi.
2. Giải nén runtime vào `~/.local/opt/census/releases/<12 hex đầu của sha256 SHA256SUMS>/python`, tạo venv **tại chỗ
   cuối cùng** bằng chính runtime đó (venv ghi đường dẫn tuyệt đối vào `pyvenv.cfg` và shebang, nên không dựng ở chỗ khác
   rồi `mv`), cài `pip install --no-index --find-links wheels --require-hashes`, rồi app `--no-deps`. Thử import trước khi
   đánh dấu `.complete`; lỗi giữa chừng thì `trap` xoá bản dở.
3. Symlink `~/.local/opt/census/current` và `~/.local/bin/census` đổi bằng `ln -sfn … .new` + `mv -T` (nguyên tử). Lần
   chạy thứ hai thấy `.complete` của cùng bản nên chỉ đặt lại symlink.
4. `~/.local/bin/census` là script console của venv, shebang trỏ thẳng vào `…/venv/bin/python`: chạy được với `env -i` và
   `PATH` tối thiểu, không cần `activate`, `PYTHONHOME` hay `~/.bashrc`.

Không đụng `/usr/bin/python3`, không thêm gì vào `/etc/profile.d` hay `/usr/local`. Thêm `~/.local/bin` vào `PATH` là
việc của `~/.profile` của user (Ubuntu đã tự thêm nếu thư mục tồn tại khi đăng nhập), không phải của installer.

Các cách khác cũng đạt test: `uv` binary tĩnh mang vào bundle rồi `uv venv --python <runtime>` + `uv pip install
--offline`; đặt runtime chung ở `~/.local/opt/python-3.12` cho nhiều app; dùng bản `install_only` (không strip). Không
đạt: venv bằng Python 3.8 hệ thống, `pip install --user` vào Python hệ thống, cài vào `/opt` bằng sudo.

## Ghi vào báo cáo cho khách

Runtime mang theo là **của bạn**: bạn chịu trách nhiệm vá nó (CVE của CPython, OpenSSL tĩnh trong bản standalone), không
phải `apt upgrade` của bệnh viện. Ghi phiên bản runtime vào ma trận hỗ trợ (bài advanced 02) và lịch phát hành bản vá.
