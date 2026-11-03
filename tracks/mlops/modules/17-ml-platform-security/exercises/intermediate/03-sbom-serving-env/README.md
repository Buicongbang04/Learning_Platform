---
title: SBOM cho môi trường serving - sinh bằng cyclonedx-py, kiểm ghim phiên bản, so hai bản phát hành
level: intermediate
services: []
files:
  - path: starter/sbom.py
    note: 5 hàm TODO
  - path: tests/test_sbom.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/intermediate/03-sbom-serving-env -q
---

## Mục tiêu

Khi một CVE mới của `numpy` hay `pyarrow` được công bố, câu hỏi đầu tiên là "service model nào đang chạy bản đó". SBOM (software bill of
materials) trả lời câu này mà không phải vào từng container. Bạn sinh SBOM CycloneDX cho môi trường serving bằng công cụ thật, kiểm mọi gói
có phiên bản ghim, đối chiếu với danh sách ghim bắt buộc, và so SBOM của hai bản phát hành.

## Đề bài

Công cụ: `cyclonedx-py` 7.5.0 (gói `cyclonedx-bom`, đã có trong môi trường mặc định), gọi bằng `python -m cyclonedx_py`. Hai chế độ:

- `requirements <tệp>`: đọc tệp requirements (không cài, không cần mạng). Dòng không ghim `==` cho thành phần **không có version**.
- `environment <python>`: đọc các gói đã cài trong môi trường của trình thông dịch đó. Test dùng chính môi trường đang chạy pytest (khoảng
  20 giây cho gần 500 gói).

Điền 5 hàm trong `starter/sbom.py`:

1. `generate(source, out, kind="requirements", timeout=300)`: chạy `cyclonedx_py` bằng `sys.executable -m cyclonedx_py <kind> ...`, định
   dạng JSON, **CycloneDX 1.6**, ghi ra `out`, trả nội dung đã đọc lại thành dict. `kind` khác `requirements` và `environment` thì
   `raise ValueError` (không chạy gì). Lệnh lỗi thì ném lỗi, không trả SBOM rỗng.
2. `packages(sbom)`: dict `{tên: version}` từ `components`, version `None` khi thành phần không có. Tên **chuẩn hoá** theo PEP 503: chữ
   thường, mọi chuỗi `-`, `_`, `.` liên tiếp thành một `-` (`Scikit_Learn` thành `scikit-learn`).
3. `unpinned(sbom)`: danh sách tên (đã chuẩn hoá, sắp xếp) không có version.
4. `diff(old, new)`: `{"added": [...], "removed": [...], "changed": {tên: [version cũ, version mới]}}`, các danh sách và khoá theo thứ tự
   tên.
5. `check(sbom, required)`: `required` là `{tên: version}` bắt buộc (tên có thể chưa chuẩn hoá). Trả danh sách đã sắp xếp gồm
   `unpinned:<tên>` cho mỗi thành phần không có version, `missing:<tên>` khi gói bắt buộc không có trong SBOM, `mismatch:<tên>` khi có
   version mà khác (tên trong mã đều đã chuẩn hoá).

Test sinh tệp requirements serving (có extras, environment marker, `--hash` xuống dòng, dòng không ghim), kiểm SBOM là CycloneDX 1.6 có
`serialNumber`, liệt kê đúng gói và version, và SBOM môi trường khớp `importlib.metadata.version` của `numpy`, `scikit-learn`,
`safetensors`, `model-signing`, `mlflow`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/intermediate/03-sbom-serving-env -q` pass.
- Bạn giải thích được vì sao SBOM sinh từ requirements không ghim là SBOM vô dụng cho việc tra CVE, và vì sao SBOM nên sinh từ **image
  đã build** (môi trường thật) chứ không chỉ từ tệp khai báo.
- Bạn nêu được SBOM của **model** (ML-BOM của CycloneDX: dữ liệu huấn luyện, model gốc, tham số) khác SBOM phần mềm ở đâu.

## Gợi ý

### Gợi ý 1

`uv run python -m cyclonedx_py requirements --help` liệt kê cờ: `--sv` (phiên bản spec), `--of` (định dạng), `-o` (tệp ra). Cờ đặt trước
đối số vị trí.

### Gợi ý 2

`re.sub(r"[-_.]+", "-", name).lower()` là quy tắc chuẩn hoá tên của PEP 503.
