---
title: Vault dev - policy chỉ đọc một path và token TTL ngắn cho api
level: basic
services: [vault-devops]
files:
  - path: starter/policy.hcl
    note: Policy của api, 1 TODO
  - path: starter/token.sh
    note: Tạo token cho api, 1 TODO
  - path: tests/test_vault_policy.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait vault-devops
  - uv run pytest tracks/devops/modules/12-gitops-secrets/exercises/basic/02-vault-dev-policy -q -rs
---

## Mục tiêu

Cấp cho api của Olist Shop đúng quyền nó cần trong Vault: đọc secret dưới `olist/api/`, không ghi, không đọc của service khác, bằng một
token sống ngắn. Hiểu vì sao KV v2 có hai cây path `data/` và `metadata/`, và TTL, max TTL của token khác nhau thế nào.

## Đề bài

Vault chạy dev mode (`vault-devops`, mục 0 của module). Mỗi lần chạy, test tạo một KV v2 mount riêng tên `devops-ex-<id>`, ghi ba secret
bằng token root của lab:

| Path (trong mount) | Của ai |
| --- | --- |
| `olist/api/db` (`username`, `password`) | api |
| `olist/api/redis` (`password`) | api |
| `olist/payments/stripe` (`api_key`) | service thanh toán, api không được đọc |

1. `starter/policy.hcl` là bản "cho chạy được trước đã" của sprint trước. Viết lại để token mang policy này chỉ được:
   - đọc mọi secret dưới `olist/api/` (cả phiên bản cũ của KV v2);
   - liệt kê tên secret dưới `olist/api/`;
   - không gì khác: không ghi, patch, xoá, xoá metadata, không đọc `olist/payments/`, không liệt kê `olist/`.

   Viết tên mount là `KV_MOUNT`; test thay bằng mount thật trước khi `vault policy write`.
2. `starter/token.sh` tạo token cho api và in đúng một dòng là token. Script nhận `POLICY_NAME` (policy test đã ghi) và `TOKEN_TTL` tuỳ
   chọn, chạy với `VAULT_ADDR` và `VAULT_TOKEN` (root của lab) có sẵn trong env. Yêu cầu:

   | Thuộc tính | Giá trị |
   | --- | --- |
   | Policy | chỉ `default` và `POLICY_NAME` |
   | TTL | `TOKEN_TTL` nếu có, mặc định 15 phút |
   | Gia hạn tối đa | 1 giờ kể từ lúc tạo, gia hạn bao nhiêu cũng không quá |

**Cách test chấm.** Mọi lệnh `vault` chạy trong sandbox với env chỉ có `VAULT_ADDR` của `vault-devops`, token và `HOME` tạm (không đọc
`VAULT_*` hay `~/.vault-token` của bạn).

| Test | Kiểm |
| --- | --- |
| `test_policy_accepted` | `vault policy write` nhận policy |
| `test_token_only_carries_lab_policy` | `vault token lookup` (bằng root) trả policies đúng `default` và policy của lab |
| `test_token_ttl_is_short` | `creation_ttl` và `ttl` từ 1 tới 900 giây, `explicit_max_ttl` từ 1 tới 3600 giây |
| `test_token_reads_its_path` | Token đọc được `password` của `olist/api/db` (so với giá trị đã ghi, không in ra) và liệt kê `olist/api` ra đúng `db`, `redis` |
| `test_token_cannot_write_or_wander` | 8 thao tác ngoài quyền đều `permission denied`: `kv put`, `kv patch`, `kv delete`, `kv metadata delete` trên `olist/api/db`, `kv get olist/payments/stripe`, `kv list olist`, `policy read`, `token create` |
| `test_token_expires` | `TOKEN_TTL=10s`: token đọc được ngay, 12 giây sau thì không |

Cuối cùng test thu hồi mọi token `token.sh` đã in ra (kể cả khi output sai định dạng), xoá policy và tắt mount. Khoảng 20 giây. Test bị
giết giữa chừng (Ctrl-C hai lần, SIGKILL) có thể để lại mount `devops-ex-<id>`, policy và token trong Vault dev; dev mode chỉ giữ dữ liệu
trong RAM, nên tắt rồi bật lại `vault-devops` (hai lệnh trong mục 0 của module) là sạch.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao `path "KV_MOUNT/olist/api/*"` không cho đọc gì trên KV v2.
- Nói được khác biệt giữa `ttl`, `explicit_max_ttl` và `period`, và vì sao token của app nên ngắn hạn.

## Gợi ý

### Gợi ý 1

Thử từng lệnh bằng tay với token con: `vault token create -policy=... -field=token`, rồi `VAULT_TOKEN=<token> vault kv get
-mount=... olist/api/db`. Thông báo `permission denied` kèm path của API (`<mount>/data/...`, `<mount>/metadata/...`) cho biết policy cần
ghi path nào. `vault kv get -output-policy -mount=... olist/api/db` in luôn policy tối thiểu cho một lệnh.

### Gợi ý 2

`vault token create -h`: xem `-ttl`, `-explicit-max-ttl`, `-period`, `-policy`. Trong Bash, `${TOKEN_TTL:-15m}` lấy biến nếu có, không thì
giá trị mặc định.
