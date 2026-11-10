---
title: Kiểm tương thích OS cũ trước chuyến đi
level: basic
services: []
files:
  - path: starter/compat_check.py
    note: Hàm check_host và CLI, bạn viết
  - path: app-requirements.yaml
    note: Yêu cầu của app ledger-agent (không sửa)
  - path: tests/fixtures
    note: Output thật của ldd --version, python3 -V, /etc/os-release trên bank, factory, hospital, lab-open
  - path: tests/test_compat_check.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/basic/03-compat-check -q
---

## Mục tiêu

Phát hiện "máy này quá cũ cho app" ở văn phòng, từ ba lệnh khách gõ giúp qua screen-share, rẻ hơn rất nhiều so với phát
hiện lúc đang cài. Bài này viết công cụ đọc **output thật** của các lệnh đó trên bốn máy khách và đối chiếu với yêu cầu
của một app, ra danh sách vấn đề có cấu trúc để đưa vào báo cáo.

## Đề bài

Mỗi máy là một thư mục có ba tệp, chính là output khách gửi lại (đã ghi trên golden của các hồ sơ, xem `tests/fixtures/`):

| Tệp | Lệnh | Ghi chú |
| --- | --- | --- |
| `ldd.txt` | `ldd --version 2>&1` | Dòng đầu dạng `ldd (<nhà phân phối>) <phiên bản>`, mỗi distro một kiểu |
| `python3.txt` | `python3 -V 2>&1` | Có thể là lỗi của shell khi máy không có `python3` |
| `os-release` | `cat /etc/os-release` | Giá trị có thể có hoặc không có dấu nháy |

Yêu cầu của app là một tệp YAML (ví dụ `app-requirements.yaml`); mọi số phiên bản, ngày là chuỗi:

| Khoá | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `glibc_min` | có | glibc tối thiểu, vd. `"2.31"` |
| `python_min` | có | Python tối thiểu dạng `"X.Y"` |
| `python_max` | không | Python tối đa dạng `"X.Y"` |
| `os_supported` | có | `{ID: [VERSION_ID, …]}` theo `/etc/os-release` |
| `as_of` | có | Ngày đối chiếu vòng đời, `"YYYY-MM-DD"` |
| `os_eol` | không | `{ID: {VERSION_ID: "YYYY-MM-DD"}}`: ngày OS hết hỗ trợ |

Viết `starter/compat_check.py`:

**`check_host(host_dir: Path, requirements: dict) -> list[dict]`** trả danh sách vấn đề, mỗi vấn đề là dict có ít nhất
`code` và `found` (được thêm khoá khác, vd. `required`, `detail`), mỗi `code` tối đa một lần, theo đúng các quy tắc:

| `code` | Khi nào | `found` |
| --- | --- | --- |
| `glibc_too_old` | Phiên bản glibc (token cuối của dòng đầu `ldd.txt` bắt đầu bằng `ldd `) nhỏ hơn `glibc_min` | Phiên bản glibc, vd. `"2.28"` |
| `python_missing` | `python3.txt` không có `Python X.Y.Z` | `None` |
| `python_too_old` | `X.Y` của Python nhỏ hơn `python_min` | Phiên bản đầy đủ, vd. `"3.8.10"` |
| `python_too_new` | Có `python_max` và `X.Y` lớn hơn nó | Phiên bản đầy đủ |
| `os_unsupported` | Không có mục nào trong `os_supported[ID]` **khớp** `VERSION_ID` | `"<ID> <VERSION_ID>"`, vd. `"ubuntu 20.04"` |
| `os_eol` | Ngày hết hỗ trợ ≤ `as_of` | Ngày hết hỗ trợ đó |

- So phiên bản theo số từng phần (`3.10` > `3.8`, `2.31` > `2.28`), không theo chuỗi.
- Một mục `E` **khớp** `VERSION_ID` khi `VERSION_ID == E` hoặc `VERSION_ID` bắt đầu bằng `E` + `"."` (mục `"8"` khớp
  `8.10`; mục `"8.1"` không khớp `8.10`).
- Ngày hết hỗ trợ: mục khớp đầu tiên trong `os_eol[ID]` nếu có; không có thì `SUPPORT_END` trong `os-release` nếu có;
  không có cả hai thì không xét. Ngày so như chuỗi `YYYY-MM-DD`.

**CLI** `python compat_check.py <requirements.yaml> <thư mục máy>...` in ra stdout một JSON object: khoá là **tên** thư mục
máy (theo đúng thứ tự tham số), giá trị là danh sách vấn đề như trên. Mã thoát `1` nếu có ít nhất một vấn đề, `0` nếu
không máy nào có vấn đề.

## Tiêu chí đạt

- `test_given_app_on_four_profiles`: với `app-requirements.yaml`, đúng tập `code` và `found` cho cả bốn máy.
- `test_random_requirements`: 40 bộ yêu cầu sinh ngẫu nhiên mỗi lần chạy (ngưỡng glibc, Python, danh sách OS, ngày đối
  chiếu, bảng vòng đời), mỗi bộ trên cả bốn máy; thư mục máy được chép sang tên ngẫu nhiên.
- `test_cli_prints_json_and_exit_code`: CLI chạy trong sandbox, JSON đúng khoá, đúng thứ tự, đúng vấn đề; mã thoát `1`
  khi có vấn đề, `0` khi chỉ đưa máy không có vấn đề.
- `test_fixtures_are_the_real_profiles` chỉ kiểm dữ liệu của bài.

## Gợi ý

### Gợi ý 1

Mở bốn thư mục trong `tests/fixtures/` và đọc từng tệp bằng mắt trước khi viết regex: cùng một thông tin, bốn máy viết
bốn kiểu.

### Gợi ý 2

`"3.10" < "3.8"` là `True` khi so chuỗi.

### Gợi ý 3

`os-release` là cú pháp shell đơn giản: `KEY=value` hoặc `KEY="value"`. Đừng dựa vào thứ tự dòng.
