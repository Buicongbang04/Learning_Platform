---
title: Mirror pip nội bộ kiểu simple index
level: basic
services: []
files:
  - path: starter/simple_index.py
    note: 2 hàm TODO
  - path: tests/test_simple_index.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/03-airgapped-proxy/exercises/basic/03-pip-mirror -q
---

## Mục tiêu

Wheelhouse (`--find-links` một thư mục, module 02) đủ cho **một** bundle. Khi khách air-gapped có nhiều team Python cùng
cần gói, họ cần một **mirror**: một chỗ trong mạng nội bộ mà `pip`/`uv` trỏ `--index-url` vào như PyPI. Định dạng đơn
giản nhất mà mọi công cụ hiểu là "simple repository API" (PEP 503): vài trang HTML tĩnh, phục vụ bằng bất kỳ web server
nào khách đã có. Bài này dựng mirror đó từ một thư mục wheel/sdist đã được duyệt.

## Đề bài

Viết trong `starter/simple_index.py`:

**`normalize(name) -> str`**: tên project chuẩn hoá theo PEP 503 (`Acme.Report_Tools` → `acme-report-tools`).

**`build_index(dist_dir, out_dir) -> dict[str, list[str]]`**: đọc mọi tệp `*.whl` và `*.tar.gz` trong `dist_dir` (bỏ qua
tệp khác, kể cả `.whl.part` đang tải dở), ghi vào `out_dir`:

- `out_dir/simple/index.html`: mỗi project (tên đã chuẩn hoá) đúng **một** thẻ `<a>`, chữ trong thẻ là tên project.
- `out_dir/simple/<project>/index.html`: mỗi tệp của project một thẻ `<a>`, chữ trong thẻ là **tên tệp**, `href` là đường
  dẫn **tương đối** tới bản sao của tệp nằm **trong** `out_dir` (cách sắp xếp bên trong `out_dir` tuỳ bạn), kèm
  `#sha256=<hex>` của tệp. Wheel có `Requires-Python` trong `METADATA` thì thẻ có `data-requires-python="…"` (escape HTML:
  `>=3.8` thành `&gt;=3.8`); sdist không cần.
- Trả `{project chuẩn hoá: [tên tệp…] sắp xếp}`.

Tên project lấy từ tên tệp (wheel: phần trước dấu `-` đầu tiên; sdist: phần trước `-<version>`), không cần đọc `METADATA`
để lấy tên. Chạy lại trên cùng đầu vào phải ra đúng cùng nội dung.

## Tiêu chí đạt

- `test_normalize`: ví dụ của PEP 503.
- `test_layout_and_return_value`: giá trị trả về; trang gốc liệt kê mỗi project một lần; có trang của từng project.
- `test_links_hashes_and_requires_python`: mỗi tệp có đúng một liên kết, `href` trỏ tới bản sao trùng byte nằm trong
  `out_dir`, `#sha256=` đúng; bản `2.0.0` mang `data-requires-python="&gt;=3.99,&lt;4"`; sdist không mang thuộc tính này.
- `test_rebuild_is_stable`: chạy hai lần cho cùng mọi tệp trong `out_dir`.
- `test_uv_installs_from_mirror`: test phục vụ `out_dir` bằng `http.server` trên `127.0.0.1`, `uv pip install
  --index-url http://127.0.0.1:<cổng>/simple/ ACME_report.tools` phải cài bản `1.5.0` (bản `2.0.0` đòi Python không có).
- `test_pip_rejects_tampered_file`: test thay tệp `law_ocr-0.3.1` trong mirror bằng một wheel khác cùng tên; `pip install`
  từ mirror phải **từ chối** vì sai hash (`pip==25.2` qua `uvx`, tải một lần; không có mạng lần đầu thì test này skip).

## Gợi ý

### Gợi ý 1

PEP 503 ngắn, đọc hết. Phần chuẩn hoá tên là một biểu thức chính quy một dòng.

### Gợi ý 2

`Requires-Python` nằm trong tệp `*.dist-info/METADATA` bên trong wheel (wheel là tệp zip); định dạng là header kiểu email,
thư viện chuẩn đọc được.

### Gợi ý 3

`pip` kiểm `#sha256=` trên liên kết mà mirror đưa ra; `uv pip install` thì chỉ kiểm khi bạn đưa hash trong tệp
requirements. Mirror sai hash là thứ bạn chỉ phát hiện khi một khách dùng `pip`.
