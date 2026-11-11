# Lời giải: policy chỉ đọc và token TTL ngắn

## Policy

```hcl
path "KV_MOUNT/data/olist/api/*" {
  capabilities = ["read"]
}

path "KV_MOUNT/metadata/olist/api/*" {
  capabilities = ["list"]
}
```

KV v2 không lưu secret ở path bạn gõ. `vault kv get -mount=secret olist/api/db` gọi `GET secret/data/olist/api/db`; `vault kv list` gọi
`LIST secret/metadata/olist/api/`; `kv delete` là `DELETE secret/data/...` (xoá mềm phiên bản mới nhất), `kv metadata delete` là
`DELETE secret/metadata/...` (xoá vĩnh viễn mọi phiên bản), `kv patch` cần capability `patch` trên `data/`. Vì vậy:

- `read` trên `data/olist/api/*` đọc được mọi phiên bản (`-version=N` cũng qua `data/`).
- `list` trên `metadata/olist/api/*` liệt kê tên secret; glob `*` khớp cả chuỗi rỗng nên khớp `metadata/olist/api/`.
- Không có gì trên `metadata/olist/` nên `kv list olist` bị từ chối; không có gì dưới `payments/`.
- Policy cũ `KV_MOUNT/*` với cả `create`, `update`, `delete` cho api quyền xoá vĩnh viễn secret của service thanh toán.

## Token

```bash
vault token create \
  -policy="$POLICY_NAME" \
  -ttl="${TOKEN_TTL:-15m}" \
  -explicit-max-ttl=1h \
  -display-name=olist-api \
  -field=token
```

- Ghi `-policy` thì token con không kế thừa policy `root` của token cha; Vault luôn thêm `default` (cho `token lookup-self`, `renew-self`).
  Không muốn cả `default` thì thêm `-no-default-policy`.
- `-ttl`: sống bao lâu nếu không gia hạn. Dev mode mặc định 768 giờ, đúng cái bản starter tạo ra.
- `-explicit-max-ttl`: trần cứng tính từ lúc tạo; app gia hạn mỗi 10 phút thì token vẫn chết ở mốc 1 giờ và app phải đăng nhập lại.
- `-period` (không dùng ở đây): token gia hạn được mãi, mỗi lần tối đa một period. Dùng cho daemon chạy lâu, thường kèm auth method có
  danh tính như Kubernetes auth.
- `-field=token` in đúng token. Ngoài bài tập, đừng in token ra log; app lấy token qua Vault Agent hay auth method, không qua script.

## Ngoài lab

Token tĩnh tạo bằng root chỉ để học policy và TTL. Production không có token root dùng hằng ngày: app đăng nhập bằng danh tính của nó
(Kubernetes auth với ServiceAccount token, AWS IAM auth...), nhận token TTL ngắn gắn policy theo role, và đọc dynamic secret (Database
secrets engine sinh user Postgres riêng cho mỗi lần đăng nhập, tự xoá khi lease hết). Mục 5 của module nói về các cách này.
