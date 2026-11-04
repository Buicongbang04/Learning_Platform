# Lời giải: SBOM cho môi trường serving

`sbom.py` cạnh tệp này là bản tham khảo.

- **Gọi công cụ bằng `sys.executable -m cyclonedx_py`** để chắc chạy đúng bản trong môi trường của dự án; `check=True` để lệnh lỗi thành
  ngoại lệ, không thành một SBOM rỗng trông như "không có gói nào".
- **Chuẩn hoá tên theo PEP 503** trước khi so: `Scikit_Learn`, `scikit-learn`, `scikit.learn` là cùng một gói. Không chuẩn hoá thì diff
  báo "xoá một gói, thêm một gói" cho cùng một thứ.
- **Thành phần không có version là lỗi.** SBOM để trả lời "đang chạy bản nào"; dòng `safetensors>=0.4` không trả lời được. Đó là lý do
  file khoá (lock) của serving phải ghim đủ, kể cả gói gián tiếp, như `uv pip compile --generate-hashes` hay `uv.lock`.
- **SBOM từ môi trường thật.** Requirements là ý định, môi trường đã cài là sự thật (gói gián tiếp, gói cài thêm tay trong Dockerfile). Ở
  production, sinh SBOM từ image đã build: `cyclonedx-py environment` trong một bước build, hoặc công cụ quét image như Syft
  (`syft <image> -o cyclonedx-json`), rồi đính SBOM vào image (attestation) hay lưu cạnh model trên registry.

**Dùng SBOM.** Khi có CVE: tra mọi SBOM đang deploy xem gói và version bị ảnh hưởng (Dependency-Track, Grype đọc được CycloneDX). Khi phát
hành: `diff` SBOM bản mới với bản đang chạy là phần bắt buộc của review (gói lạ mới xuất hiện là dấu hiệu cần hỏi).

**ML-BOM.** CycloneDX 1.5+ có loại thành phần `machine-learning-model` và `data`, cùng model card: ghi model gốc (vd. checkpoint tải từ Hugging
Face kèm hash), dataset huấn luyện và phiên bản, tham số. SBOM phần mềm trả lời "code nào đang chạy"; ML-BOM trả lời "model này làm từ gì".
