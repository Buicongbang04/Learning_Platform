# Lời giải: kiểm tương thích OS cũ trước chuyến đi

Lời giải ở `compat_check.py` cạnh tệp này:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/basic/03-compat-check -q
```

## Kết quả với `app-requirements.yaml` (ledger-agent 2.0)

| Máy | Vấn đề | Đọc thế nào |
| --- | --- | --- |
| `bank` (Rocky 8.10) | `glibc_too_old` (2.28 < 2.31), `python_missing` | Wheel `manylinux_2_31` không cài được trên glibc 2.28; Rocky 8 chỉ có `platform-python` 3.6 cho công cụ hệ thống, `python3` không được cài (`bash: python3: command not found`). Hai việc: xin product wheel `manylinux_2_28` (hoặc 2014), và mang Python riêng |
| `factory` (Debian 12) | — | Python 3.11.2, glibc 2.36: đạt |
| `hospital` (Ubuntu 20.04) | `python_too_old` (3.8.10), `os_unsupported`, `os_eol` (2025-05-31) | App không chạy trên 3.8; 20.04 ngoài danh sách hỗ trợ và đã hết standard support. Báo khách bằng văn bản; nếu vẫn phải cài thì mang Python 3.12 riêng (bài intermediate 02) và ghi rõ đó là ngoại lệ |
| `lab-open` (Ubuntu 22.04) | — | Đạt |

Rocky 8 có `SUPPORT_END="2029-05-31"` trong `os-release` nên không bị `os_eol` với `as_of` 2026-11-11; Ubuntu và Debian
không có khoá đó, vòng đời phải lấy từ bảng `os_eol` của yêu cầu.

## Cách làm

- **glibc:** dòng đầu bắt đầu bằng `ldd ` (Rocky `ldd (GNU libc) 2.28`, Ubuntu `ldd (Ubuntu GLIBC 2.31-0ubuntu9.18) 2.31`,
  Debian `ldd (Debian GLIBC 2.36-9+deb12u14) 2.36`), lấy token cuối. Đừng lấy số đầu tiên gặp được: phần trong ngoặc có
  bản vá của distro.
- **Python:** regex `^Python (\d+)\.(\d+)(\.\d+)?` theo dòng; không khớp (vd. `bash: python3: command not found`) là
  `python_missing`. So `(major, minor)` dạng tuple số.
- **os-release:** tách `KEY=value`, bỏ nháy đơn/kép; khớp phiên bản bằng "bằng hoặc tiền tố + `.`" để `"8"` khớp `8.10`
  mà `"8.1"` không khớp.
- **Vòng đời:** bảng của yêu cầu trước, `SUPPORT_END` sau; so chuỗi ISO là đủ.
- CLI giữ thứ tự tham số (dict Python giữ thứ tự chèn), mã thoát `1` khi có vấn đề để dùng được trong script preflight.

Thường sai: so phiên bản bằng chuỗi (`"3.10" < "3.8"`), lấy `VERSION` thay `VERSION_ID`, coi `ID_LIKE=rhel` là `rhel`
(app hỗ trợ "RHEL 8" chưa chắc đã hỗ trợ Rocky: hỏi product), quên rằng `python3 -V` của Python 2 cũ in ra stderr (đã gộp
`2>&1` nên vẫn đọc được).
