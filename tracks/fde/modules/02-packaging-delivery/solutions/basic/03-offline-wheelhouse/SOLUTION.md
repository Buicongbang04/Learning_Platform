# Lời giải: Wheelhouse offline cho một app Python

Lời giải là `build_bundle.sh` và `install.sh` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/basic/03-offline-wheelhouse -q
```

Đo trên laptop của repo (2026-11-04): build ~5 s khi cache trống, cả bài ~18 s, bundle ~5 MB.

## Ba chỗ hỏng do máy khách, đều thật

| Làm "như ở nhà" | Trên `lawfirm-staging` | Nguyên nhân |
| --- | --- | --- |
| `python3 -m pip install -r requirements.txt` trên VM | `No module named pip`; có pip thì cũng lỗi phân giải tên `pypi.org` | Cloud image không có pip; egress `none`: không route, không DNS |
| `pip download -r requirements.txt` trên laptop rồi mang wheel đi | `No matching distribution found for pydantic-core==2.33.2` | Laptop chạy CPython 3.12 nên tải wheel `cp312`; máy khách là CPython **3.10** (`cp310`). Gói thuần Python (`py3-none-any`) thì lọt, gói có phần biên dịch thì không |
| `python3 -m venv ~/intake` | `ensurepip is not available … apt install python3.10-venv` | Cloud image Ubuntu không có gói `python3-venv`; máy không mạng và khách không cho cài gói hệ thống |

Một bẫy thứ tư không báo lỗi: `--system-site-packages` (hay cài `--user` vào Python hệ thống) làm `import yaml` lấy
**PyYAML 5.4.1** của gói `python3-yaml` Ubuntu thay cho 6.0.2 đã ghim. Test bắt ca này bằng phiên bản app tự báo.

## Cách làm

**Build (máy bạn):**

1. `uv export --frozen --no-dev --no-emit-project` ⇒ `requirements.txt` có hash của mọi wheel trong lock.
2. `uv build --wheel` ⇒ wheel của chính `intake` (thuần Python, cài được ở mọi nơi).
3. `uvx --from pip==25.1.1 pip download --only-binary=:all: --python-version 3.10 --implementation cp --abi cp310
   --abi abi3 --abi none --platform manylinux_2_35_x86_64 … --platform manylinux2014_x86_64 --require-hashes`.
   Thông số đo trên VM: `python3 --version` = 3.10.12, `ldd --version` = glibc 2.35 ⇒ nhận mọi tag manylinux tới
   `2_35`. `--only-binary=:all:` là bắt buộc khi đặt nền tảng khác máy mình: pip không được build sdist cho máy khác.
4. Tải thêm **wheel của pip** vào bundle. Wheel là tệp zip chạy được: `python pip-25.1.1-py3-none-any.whl/pip install …`
   là cách pip tự cài chính nó (tài liệu pip "Installing pip"), không cần `ensurepip`.
5. Ghi `SHA256SUMS` cho cả bundle.

**Install (máy khách):**

1. `sha256sum -c SHA256SUMS` trước tiên.
2. `python3 -m venv --without-pip ~/intake`: module `venv` có sẵn, chỉ `ensurepip` bị Ubuntu tách ra.
3. Chạy pip từ wheel với `--no-index --find-links wheels --require-hashes -r requirements.txt`, rồi app với `--no-deps`.
   `--no-index` biến mọi thiếu sót thành lỗi ngay thay vì treo chờ mạng.
4. Thử `import` trước khi báo xong.

## Các đường khác cũng đạt

- Mang binary `uv` (bản phát hành tĩnh, ghim sha256) vào bundle và `uv venv --python /usr/bin/python3` + `uv pip install
  --offline --no-index --find-links`. Gọn hơn, đổi lại phải xin duyệt thêm một binary.
- `uv pip install --target <dir> --python-platform x86_64-manylinux_2_35 --python-version 3.10` ngay trên laptop rồi mang
  thư mục `site-packages` đã cài; nhanh khi cài nhưng không còn "wheel + hash" để IT khách kiểm.

Không đạt ràng buộc của khách: mang Python riêng (python-build-standalone) hay xin cài `python3-venv`. Cả hai hợp lý ở
khách khác, nhưng đề yêu cầu đúng Python của hệ điều hành; ghi rõ đánh đổi này trong tài liệu bundle.

## Lưu ý về bundle Python thật

Wheelhouse gắn chặt với **một** bộ (Python, ABI, glibc, kiến trúc). Khách thứ hai chạy RHEL 8 (Python 3.6 hệ thống)
cần wheelhouse khác hoặc một chiến lược khác (container, Python mang theo). Đây là lý do bundle trong module ghi rõ "đích"
trong manifest và preflight kiểm nó trước khi cài.
