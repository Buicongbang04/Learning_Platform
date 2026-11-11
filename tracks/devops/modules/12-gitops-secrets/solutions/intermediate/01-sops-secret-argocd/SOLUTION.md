# Lời giải: Secret mã hoá bằng SOPS + age, ArgoCD giải mã khi sync

## `.sops.yaml`

```yaml
creation_rules:
  - path_regex: shop/.*\.enc\.yaml$
    encrypted_regex: ^(data|stringData)$
    age: >-
      TEAM_AGE_RECIPIENT,
      ARGOCD_AGE_RECIPIENT
```

- `path_regex` so với đường dẫn tệp (ở đây là đích nhờ `--filename-override`); rule đầu tiên khớp được dùng. Repo nhiều môi trường thường
  có một rule mỗi môi trường, mỗi rule một bộ recipient (Advanced 01).
- `encrypted_regex` chỉ mã hoá giá trị dưới `data`, `stringData`. Thiếu nó, SOPS mã hoá mọi giá trị kể cả `kind` và `metadata.name`: vẫn
  giải mã được, nhưng PR không còn đọc được gì và diff không nói Secret nào đổi.
- Hai recipient: team giải mã được để sửa; ArgoCD giải mã được để sync. Thiếu recipient của ArgoCD, sidecar lỗi
  `failed to get the data key` và Application báo ComparisonError.

## `seal.sh`

```bash
sops encrypt --filename-override "$target" --output "$target" "$plain"
```

SOPS sinh một data key ngẫu nhiên, mã hoá từng giá trị bằng AES256-GCM với data key đó, rồi bọc data key cho từng recipient age (khối
`sops.age[].enc`). MAC trên toàn bộ giá trị phát hiện ai đó sửa bản mã. Thêm recipient là bọc lại data key (`sops updatekeys`), không
động tới giá trị. Script kiểm đuôi `.enc.yaml` vì cả creation_rule lẫn plugin của ArgoCD dựa vào đuôi đó.

## Kustomize và Application

`kustomization.yaml` liệt kê `olist-db.enc.yaml` như một tệp thường. Kustomize thuần sẽ apply nguyên bản mã hoá (và lỗi vì `sops:` không
phải trường của Secret); plugin `sops-kustomize` trong sidecar của repo-server chạy `sops --decrypt --in-place` cho mọi `*.enc.yaml` trong
bản sao của repo rồi mới `kustomize build`. Application chọn plugin bằng:

```yaml
spec:
  source:
    plugin:
      name: sops-kustomize
```

## Sau khi sync, giá trị nằm đâu

- Không trong repo: test quét mọi tệp tìm giá trị, base64 của giá trị và `AGE-SECRET-KEY-`.
- Trong etcd, như mọi Secret (mã hoá at rest nếu cluster bật encryption provider).
- Trong cache redis của ArgoCD (manifest đã render) và trong pod. Ai có quyền `get secret` trong namespace đọc được giá trị: SOPS bảo vệ
  Git, không bảo vệ cluster. RBAC và quyền đọc Secret vẫn là việc phải làm.

## Xoay khoá và xoay giá trị

- Thêm người: thêm recipient vào `.sops.yaml`, `sops updatekeys shop/olist-db.enc.yaml`, commit.
- Một khoá có thể đã lộ: gỡ recipient, `updatekeys`, **và** xoay mật khẩu Postgres, vì mọi commit cũ trong lịch sử vẫn mở được bằng khoá
  cũ.
- Khoá của ArgoCD đổi (admin tạo khoá mới): mọi tệp phải `updatekeys` với recipient mới trước khi thay Secret khoá trong cluster, nếu
  không sync sẽ lỗi.

## Sai lầm hay gặp

- `sops decrypt shop/olist-db.enc.yaml > shop/olist-db.yaml` để sửa rồi quên xoá: bản rõ vào commit sau. Sửa bằng `sops edit`, hay giải mã
  ra stdout.
- Đặt `SOPS_AGE_KEY_FILE` trỏ vào thư mục trong repo: khoá riêng đi theo `git add -A`. `gitops_repo` của test từ chối tệp có
  `AGE-SECRET-KEY-`; repo thật nên có pre-commit hook làm việc tương tự (module 03).
- `data:` với base64 thay cho mã hoá: base64 là encoding, test bắt được.
