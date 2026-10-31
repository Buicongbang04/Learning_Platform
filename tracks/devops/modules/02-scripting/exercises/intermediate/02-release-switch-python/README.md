---
title: Công cụ chuyển release bằng Python - symlink nguyên tử, check sau deploy và rollback
level: intermediate
services: []
files:
  - path: starter/release.py
    note: 5 TODO
  - path: tests/test_release.py
    note: Không sửa
run:
  - uv run python tracks/devops/modules/02-scripting/exercises/intermediate/02-release-switch-python/starter/release.py --help
  - uv run pytest tracks/devops/modules/02-scripting/exercises/intermediate/02-release-switch-python -q
---

## Mục tiêu

Viết một công cụ vận hành bằng Python đúng cách: `argparse` có subcommand, `pathlib`, `logging` ra stderr,
`subprocess` không qua shell, exit code rõ ràng, `--dry-run`, và thao tác đổi trạng thái nguyên tử. Đây là mô hình
deploy "symlink `current`" mà Capistrano, Deployer và nhiều hệ thống deploy lên VM vẫn dùng.

## Đề bài

Trên máy app, các bản Olist Shop nằm trong `<root>/releases/<version>/`, và `<root>/current` là symlink tới bản đang
chạy (systemd chạy `<root>/current/...`). Hoàn thành `starter/release.py --root <root> <lệnh>`:

**`deploy <source_dir> --version <V> [--check "<lệnh>"] [--check-timeout <giây>] [--dry-run]`**

1. `V` phải khớp `^[A-Za-z0-9][A-Za-z0-9._-]*$` (không rỗng, không `.`, `..`, không `/`, không bắt đầu bằng `.` hay
   `-`, không dấu cách). Sai thì thoát `2` (ví dụ `parser.error(...)` trong `main`, hoặc ghi lỗi rồi `return 2`), không tạo gì.
2. `source_dir` không phải thư mục: log lỗi, thoát `1`, không có traceback.
3. `current` đang trỏ tới `V`: log rằng không có gì để làm, thoát `0`, không chép, không chạy check, không đổi
   `.history`.
4. `releases/V` chưa có: chép `source_dir` vào một thư mục tạm **trong** `releases/` rồi đổi tên thành `releases/V`.
   Đã có: dùng lại, không chép lại, không đụng nội dung bên trong.
5. Chuyển `current` sang `releases/V` **nguyên tử**: tạo symlink tạm trong `<root>` rồi `os.replace` đè lên `current`.
   Đích của symlink là đường dẫn **tương đối** đúng bằng chuỗi `releases/V` (`os.readlink` trả `releases/V`).
6. Có `--check`: tách chuỗi bằng `shlex.split`, chạy bằng `subprocess.run` (**không** `shell=True`, không
   `os.system`) với thư mục làm việc là `releases/V`, biến môi trường `RELEASE_VERSION=V` (cộng môi trường hiện có),
   timeout `--check-timeout` giây (mặc định `30`). Check thoát khác `0`, quá giờ, hoặc không chạy được (lệnh không tồn
   tại): chuyển `current` về bản trước (nếu trước đó chưa có `current` thì xoá `current`), log lỗi, thoát `1`, không
   đổi `.history`, không có traceback. Thư mục `releases/V` vừa chép được giữ lại để điều tra.
7. Thành công: thêm một dòng `V` vào cuối `<root>/.history`, thoát `0`.
8. `--dry-run`: kiểm như bước 1–3, log những gì sẽ làm, thoát `0`; **không** tạo, sửa, xoá tệp nào, không chạy check.

**`rollback [--dry-run]`**: `.history` có ít hơn 2 dòng: log lỗi, thoát `1`. Ngược lại chuyển `current` về dòng áp
chót, bỏ dòng cuối khỏi `.history`, thoát `0`. Ví dụ deploy `v1`, `v2`, `v3` rồi rollback: `current` là `v2`,
`.history` là `v1 v2`; rollback lần nữa ra `v1`; lần thứ ba thoát `1`. Rollback không xoá release nào. `--dry-run`
không đổi gì.

**`status`**: in tên release `current` đang trỏ tới kèm xuống dòng ra stdout, thoát `0`; chưa có `current` thì stdout
rỗng, thoát `1`.

Quy ước chung:

- Mọi log đi qua `logging` ra **stderr**; `deploy` và `rollback` để stdout rỗng. Mỗi lần `deploy` có ít nhất một dòng
  log.
- Option hay lệnh con sai: `argparse` tự thoát `2`.
- Sau mọi thao tác, `<root>` chỉ chứa `releases`, `current` (nếu có) và `.history` (nếu có); `releases/` chỉ chứa thư
  mục release. Không để lại symlink tạm, tệp tạm hay thư mục tạm.
- Đường dẫn `<root>` có thể chứa dấu cách.

Test chạy `release.py` bằng `subprocess` với chính Python của bạn và một script check giả ghi lại thư mục làm việc,
`RELEASE_VERSION`, rồi trả `0` khi tệp `HEALTH` trong release chứa `ok`. Một test truyền
`--check "<python> <checker> <log> ; touch <tệp>"` và kiểm `<tệp>` **không** được tạo (chuỗi không đi qua shell). Test
cũng tìm chuỗi `shell=True` và `os.system(` trong mã nguồn.

Mọi test chạy script của bạn trong sandbox bubblewrap (xem [Cài đặt](../../../README.md#0-cài-đặt)): `/` chỉ đọc, `/tmp` thật bị che, thư mục làm việc và thư mục duy nhất ghi được là thư mục tạm của test, môi trường biến dựng lại từ đầu (chỉ có `PATH`, `HOME` trỏ vào thư mục tạm, `LANG`/`LC_ALL`, cộng các biến test đặt). Thiếu `bwrap` thì test skip.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/02-scripting/exercises/intermediate/02-release-switch-python -q` pass toàn bộ.
- Giải thích được vì sao `os.remove(current)` rồi `os.symlink(...)` không nguyên tử, và chuyện gì xảy ra với request
  đến đúng khoảng giữa hai lệnh.
- Nói được vì sao `subprocess.run(f"... {user_input}", shell=True)` là lỗ hổng, và khi nào `shell=True` chấp nhận được.
- Chỉ ra ít nhất hai điểm bài này cố ý đơn giản hoá so với công cụ deploy thật (khởi động lại service, dọn release
  cũ, khoá khi hai người deploy cùng lúc...).

## Gợi ý

### Gợi ý 1

Đọc release hiện tại: `link.is_symlink()` rồi `Path(os.readlink(link)).name`. Chuyển nguyên tử:

```python
tmp = root / f".current.{os.getpid()}"
tmp.symlink_to(Path("releases") / version)
os.replace(tmp, root / "current")
```

`os.replace` gọi `rename(2)`, đè lên đích có sẵn trong một bước. Ghi `.history` cũng theo cách đó: ghi tệp tạm rồi
`os.replace`.

### Gợi ý 2

`subprocess.run(argv, cwd=..., env={**os.environ, "RELEASE_VERSION": v}, timeout=t, capture_output=True, text=True)`.
Bắt `subprocess.TimeoutExpired` (Python tự giết tiến trình con khi hết giờ) và `OSError` (gồm `FileNotFoundError`,
`PermissionError`). `shlex.split` ném `ValueError` khi chuỗi có dấu nháy không đóng. Chép thư mục:
`shutil.copytree(source, staging, symlinks=True)` rồi `staging.rename(target)`.
