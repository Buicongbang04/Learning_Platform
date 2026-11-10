# Lời giải: mirror pip nội bộ kiểu simple index

Bố cục mirror của lời giải:

```text
mirror/
├── files/                       bản sao mọi wheel/sdist (tên giữ nguyên)
└── simple/
    ├── index.html               <a href="acme-report-tools/">acme-report-tools</a> …
    ├── acme-report-tools/index.html
    │     <a href="../../files/Acme.Report_Tools-2.0.0-py3-none-any.whl#sha256=…"
    │        data-requires-python="&gt;=3.99,&lt;4">Acme.Report_Tools-2.0.0-py3-none-any.whl</a>
    └── law-ocr/index.html
```

- `normalize`: `re.sub(r"[-_.]+", "-", name).lower()` (PEP 503). Mọi biến thể `Acme.Report_Tools`, `acme_report_tools`
  gom về một trang; người dùng gõ `ACME_report.tools` vẫn tìm được.
- Tên project lấy từ tên tệp bằng regex: wheel thay `-` trong tên bằng `_` nên phần trước `-` đầu tiên là tên; sdist thì
  tên có thể chứa `-`, nên tách ở `-<chữ số>` cuối.
- `Requires-Python` đọc từ `*.dist-info/METADATA` trong zip bằng `email.parser.HeaderParser`. Thiếu thuộc tính này thì
  công cụ cài coi `2.0.0` (bản mới nhất) là ứng viên, phải tải nó về mới biết nó không hợp với Python 3.12: chậm hơn, và
  tuỳ công cụ/phiên bản có thể dừng với lỗi thay vì lùi về `1.5.0`.
- Giá trị thuộc tính đi qua `html.escape(..., quote=True)`: `<` và `>` trần trong thuộc tính làm parser HTML của một số
  công cụ đọc sai.
- `href` tương đối (`../../files/…`) để mirror chép sang máy khác, đổi tên miền, đặt sau reverse proxy của khách đều
  chạy; URL tuyệt đối `http://laptop-cua-ban:8000/…` là lỗi kinh điển khi dựng mirror ở văn phòng rồi mang sang khách.
- Ghi tệp vào `files/` chỉ khi chưa có hoặc khác sha256 ⇒ chạy lại cho cùng kết quả, không đụng mtime vô cớ.

## Vì sao test dùng cả uv lẫn pip

`pip` coi `#sha256=` trên liên kết là hash "từ internet" và **luôn** kiểm khi tải; tệp bị thay ⇒
`THESE PACKAGES DO NOT MATCH THE HASHES`. `uv pip install` (0.11) không kiểm hash của liên kết trừ khi tệp requirements có
hash (`--require-hashes`, hoặc requirements sinh bằng `uv pip compile --generate-hashes`). Bài học cho mirror ở khách:
hash trong mirror bảo vệ người dùng `pip`; với `uv`, tính toàn vẹn phải nằm trong **lockfile** của dự án, không trong mirror.

## Mirror tĩnh so với devpi / Nexus

Mirror tĩnh này không có upload, không cache tự động, không xoá bản bị yanked; đổi lại nó là vài tệp HTML mà IT nào cũng
phục vụ được (nginx, IIS, thậm chí một share tệp với `file://`) và quét virus được trước khi đưa vào vùng trong. Phần 3 của
README module so sánh với devpi, Nexus/Artifactory, `apt-mirror`.
