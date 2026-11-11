# TODO: bản "cho chạy được trước đã"; thu hẹp đúng bảng quyền trong README (KV v2: data/ và metadata/ là hai path khác nhau)
path "KV_MOUNT/*" {
  capabilities = ["create", "read", "update", "patch", "delete", "list"]
}
