---
title: Secret Postgres mã hoá bằng SOPS + age, ArgoCD giải mã khi sync
level: intermediate
services: []
files:
  - path: starter/gitops/.sops.yaml
    note: creation_rules, 1 TODO
  - path: starter/seal.sh
    note: Mã hoá một Secret rõ vào repo, 1 TODO
  - path: starter/gitops/shop/kustomization.yaml
    note: 1 TODO
  - path: starter/application.yaml
    note: 1 TODO
  - path: starter/gitops/shop/postgres.yaml
    note: Postgres đọc Secret olist-db
  - path: starter/gitops/shop/api.yaml
    note: api đọc DATABASE_URL từ Secret olist-db
  - path: tests/test_sops_secret.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/12-gitops-secrets/exercises/intermediate/01-sops-secret-argocd -q -rs
---

## Mục tiêu

Đưa mật khẩu Postgres vào repo GitOps mà repo không bao giờ chứa giá trị rõ: mã hoá theo trường bằng SOPS với hai recipient age (team
và ArgoCD), để ArgoCD giải mã lúc sync, pod đọc đúng giá trị, và team vẫn tự giải mã được khi cần sửa.

## Đề bài

Olist Shop gồm postgres, redis và api. Postgres lấy `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD` từ Secret `olist-db`; api lấy
`DATABASE_URL` (có mật khẩu bên trong) từ cùng Secret đó. Bản rõ của Secret do người giữ mật khẩu đưa cho bạn, nằm **ngoài** repo:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: olist-db
type: Opaque
stringData:
  POSTGRES_USER: olist
  POSTGRES_DB: olist
  POSTGRES_PASSWORD: <mật khẩu>
  DATABASE_URL: postgresql+psycopg://olist:<mật khẩu>@postgres:5432/olist
```

1. `gitops/.sops.yaml`: một creation_rule cho `shop/*.enc.yaml`, mã hoá cho cả `TEAM_AGE_RECIPIENT` (khoá của team) và
   `ARGOCD_AGE_RECIPIENT` (khoá của ArgoCD trong cluster), và chỉ mã hoá trường dữ liệu của Secret (`data`, `stringData`): `apiVersion`,
   `kind`, `metadata` phải còn đọc được khi review. Hai placeholder đó test thay bằng public key thật; trên repo thật bạn ghi thẳng
   `age1...`. Chỉ dùng age: sidecar của ArgoCD từ chối tệp có khoá KMS, Vault hay PGP.
2. `seal.sh <tệp rõ> <đích>`: mã hoá tệp rõ thành tệp đích trong repo theo `.sops.yaml` (rule chọn theo đường dẫn **đích**), không bao
   giờ ghi bản rõ vào repo. Test gọi `bash seal.sh /đường/ngoài/repo/olist-db.yaml shop/olist-db.enc.yaml` từ gốc `gitops/`.
3. `gitops/shop/kustomization.yaml` liệt kê `olist-db.enc.yaml`; không sinh Secret bằng `secretGenerator` từ tệp rõ.
4. `application.yaml`: ArgoCD chỉ giải mã khi render qua plugin `sops-kustomize` của cluster (mục 0 của module).

**Cách test chấm.** Khoá của team sinh bằng `age_keypair` trong thư mục tạm ngoài repo; mật khẩu sinh ngẫu nhiên mỗi lần chạy và không bao
giờ được in. Mọi lệnh `sops` chạy trong sandbox với env dựng từ đầu (không đọc `~/.config/sops` hay `SOPS_*` của bạn).

| Test | Cần cluster | Kiểm |
| --- | --- | --- |
| `test_leak_scanner_catches_plaintext` | Không | Bộ quét của test bắt được giá trị rõ và base64 của nó (chứng minh bộ quét không mù) |
| `test_sops_config_rules` | Không | Rule khớp `shop/olist-db.enc.yaml`, đúng hai recipient, `encrypted_regex` khớp `data`, `stringData` và không khớp `apiVersion`, `kind`, `metadata`, `name`, `type` |
| `test_seal_encrypts_fields_for_both_recipients` | Không | Thay hai placeholder bằng hai khoá tạm, chạy `seal.sh`: tệp đích có, không tệp nào trong repo chứa mật khẩu, base64 của mật khẩu hay của `DATABASE_URL`, hay `AGE-SECRET-KEY-`; `kind`, `metadata.name` còn rõ, mọi giá trị là `ENC[...]`; `sops.age` đúng hai recipient |
| `test_both_recipients_can_decrypt` | Không | Mỗi khoá giải mã ra đúng mật khẩu |
| `test_kustomize_includes_secret_and_workloads_use_it` | Không | `kubectl kustomize` render được, có `olist-db.enc.yaml`, postgres và api tham chiếu Secret `olist-db`, không có Secret rõ nào khác |
| `test_application_uses_sops_plugin` | Không | Plugin `sops-kustomize`, sync tự động, placeholder giữ nguyên |
| `test_argocd_decrypts_and_app_is_ready` | Có | Mã hoá với recipient thật của ArgoCD (`lab.sops_age_recipient`), đẩy repo, apply Application: `Synced`, `Healthy` trong 240 giây; `/readyz` của api trả 200 (api đăng nhập Postgres bằng mật khẩu đã giải mã) |
| `test_pods_read_the_sealed_value` | Có | Secret trên cluster đúng giá trị; `POSTGRES_PASSWORD` trong pod postgres khớp (so SHA-256, không in) |
| `test_value_not_in_argocd_status` | Có | Giá trị và base64 của nó không có trong Application hay `kubectl describe` |

Khoảng 30 giây khi đã đúng.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được SOPS mã hoá gì bằng khoá nào: data key, recipient, MAC; vì sao thêm hay gỡ recipient không phải mã hoá lại giá trị.
- Nói được ai giải mã được tệp này, khoá riêng của ArgoCD nằm đâu, và vì sao khoá riêng không bao giờ được vào repo.

## Gợi ý

### Gợi ý 1

`sops encrypt --help`: xem `--filename-override` (chọn creation_rule và định dạng theo tên khác với tên tệp đầu vào) và `--output`.
Mã hoá bằng `>` vào tệp tạm rồi `mv` cũng được, miễn là bản rõ không đi qua thư mục repo.

### Gợi ý 2

Trong `.sops.yaml`, `age:` nhận một chuỗi nhiều recipient cách nhau bằng dấu phẩy. `encrypted_regex` so với **tên khoá** YAML ở mọi cấp:
`^(data|stringData)$` mã hoá cả cây con dưới hai khoá đó. Trường `plugin` nằm trong `spec.source` của Application.
