---
title: Ký model, verify và cổng deploy gộp chữ ký với quét model
level: intermediate
services: []
files:
  - path: starter/signing.py
    note: 3 hàm TODO
  - path: tests/test_signing.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/intermediate/02-sign-verify-deploy-gate -q
---

## Mục tiêu

Ký cả thư mục model ngay khi pipeline huấn luyện tạo ra nó, và chỉ cho deploy khi chữ ký còn khớp **và** máy quét không thấy gì. Chữ ký
trả lời câu "đây có đúng là thứ pipeline của ta đã tạo không"; quét trả lời câu "thứ đó có nguy hiểm khi nạp không". Hai câu khác nhau:
một model được ký đúng vẫn có thể chứa payload nếu chính pipeline bị chiếm.

## Đề bài

Dùng thư viện `model-signing` 1.1.1 (dự án model-transparency của OpenSSF) với **cặp khoá EC P-256 mà test sinh tại chỗ**: không
Sigstore, không OIDC, không mạng. Test tạo thư mục model gồm `model.safetensors` và `config.json`, khoá `release` (hợp lệ) và `intruder`
(kẻ khác).

Điền 3 hàm trong `starter/signing.py`:

1. `sign(model_dir, private_key, signature)`: ký **cả thư mục** bằng khoá riêng EC, ghi chữ ký (bundle JSON chuẩn của model-signing, có
   `dsseEnvelope`) ra `signature`. Test verify chữ ký này bằng chính thư viện model-signing, nên không tự chế định dạng. Nếu `signature`
   nằm trong `model_dir` thì `raise ValueError` và không ghi gì (chữ ký trong thư mục sẽ thành một tệp "lạ" lúc verify).
2. `verify(model_dir, public_key, signature)`: `True` chỉ khi chữ ký hợp lệ với **đúng** khoá công khai này và thư mục khớp từng byte, đủ
   và không thừa tệp so với lúc ký. Mọi trường hợp khác trả `False`, **không** ném lỗi: thiếu tệp chữ ký, tệp rỗng, không phải JSON, JSON
   sai cấu trúc, ký bằng khoá khác, sửa một byte, thêm, xoá hay đổi tên tệp.
3. `deploy_gate(model_dir, signature, public_key, scan)`: trả `{"allowed": bool, "reasons": [...]}` với:
   - `"signature"` khi `verify` trả `False`;
   - `"scan"` khi kết quả `scan(model_dir)` không sạch: `returncode` không phải 0 hay 3, `stdout` không phải JSON object, có `issues`
     hoặc có `errors`. Khác bài 01 (cho qua issue `LOW`): đây là cổng cuối trước production, không có lớp allowlist đứng trước, nên mọi
     issue đều chặn và người duyệt quyết định ngoại lệ, thay vì để code cổng tự đánh giá mức độ.

   `reasons` theo đúng thứ tự `signature` rồi `scan`; gọi `scan` **đúng một lần** trên chính `model_dir`, kể cả khi chữ ký đã sai (để
   báo đủ mọi lý do). Test truyền `mlopskit.modelscan_run` (container không mạng) hoặc bản giả.

Pickle độc hại trong test đã vô hại hoá (nạp vào chỉ ghi một tệp đánh dấu trong thư mục tạm); code của bạn không bao giờ được nạp tệp
model, test kiểm tệp đánh dấu không xuất hiện.

Trong cổng thật, phần `scan` nên là cổng đầy đủ của bài Intermediate 01 (allowlist định dạng + modelscan); ở đây giữ đơn giản để tập trung
vào chữ ký.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/intermediate/02-sign-verify-deploy-gate -q` pass.
- Bạn giải thích được vì sao verify phải fail closed với **mọi** lỗi, kể cả lỗi "không mong đợi" như JSON hỏng.
- Bạn nêu được ai giữ khoá riêng, khoá công khai được phân phối cho cổng deploy thế nào, và khi khoá bị lộ thì làm gì (module README
  mục 6). So sánh với ký keyless bằng Sigstore.

## Gợi ý

### Gợi ý 1

```python
from model_signing import signing, verifying
signing.Config().use_elliptic_key_signer(private_key=key_path).sign(model_dir, signature_path)
verifying.Config().use_elliptic_key_verifier(public_key=pub_path).verify(model_dir, signature_path)
```

`verify` của thư viện ném `ValueError` khi không khớp, nhưng không phải mọi lỗi đều là `ValueError`.

### Gợi ý 2

`Path(signature).resolve().is_relative_to(Path(model_dir).resolve())` kiểm "nằm trong thư mục" mà không bị đánh lừa bởi `..`.
