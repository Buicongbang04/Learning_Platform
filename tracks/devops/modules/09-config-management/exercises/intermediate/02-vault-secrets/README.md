---
title: Ansible Vault - mã hoá bí mật, vault id, encrypt_string và không lộ qua --diff
level: intermediate
services: []
files:
  - path: starter/site.yml
    note: Play ghi secrets.env
  - path: starter/inventory/group_vars/workers/vars.yml
    note: Đang chứa mật khẩu rõ
  - path: starter/inventory/group_vars/workers/vault.yml
    note: Tệp vault, chưa có gì
  - path: starter/inventory/host_vars/worker-2.yml
    note: Mật khẩu Redis riêng của worker-2, đang rõ
  - path: starter/templates/secrets.env.j2
    note: Template, không cần sửa
  - path: tests/test_vault_secrets.py
    note: Không sửa
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/09-config-management/exercises/intermediate/02-vault-secrets -q -rs
---

## Mục tiêu

Đưa bí mật ra khỏi Git ở dạng rõ mà playbook vẫn đọc được: mã hoá cả tệp và từng giá trị bằng Ansible Vault có vault id, tách tên
biến thường khỏi biến vault để còn grep được, và chặn bí mật lộ qua output (`-v`, `--diff`) khi chạy trong CI.

## Đề bài

Repo cấu hình của worker đang có mật khẩu database và Redis ở dạng rõ (`starter/inventory/...`). `worker-2` nối một Redis riêng
nên có mật khẩu Redis khác. Mật khẩu vault của môi trường prod trong lab là `olist-lab-vault-2026` (ở công ty thật nó nằm trong
secret manager hay CI, không bao giờ trong repo).

| Mục | Yêu cầu test kiểm |
| --- | --- |
| Tệp vault | `inventory/group_vars/workers/vault.yml` mã hoá **cả tệp** bằng vault id `prod`: dòng đầu đúng `$ANSIBLE_VAULT;1.2;AES256;prod`. Giải mã ra đúng hai khoá `vault_olist_db_password: Olist-Db-2026!x7` và `vault_olist_redis_password: Olist-Redis-2026!k3` |
| Trỏ biến | `inventory/group_vars/workers/vars.yml` chỉ có `olist_db_password: "{{ vault_olist_db_password }}"` và `olist_redis_password: "{{ vault_olist_redis_password }}"` |
| Một giá trị | `inventory/host_vars/worker-2.yml` vẫn là YAML thường, có `vault_olist_redis_password: !vault \|` mã hoá bằng `encrypt_string` với vault id `prod`, giá trị `Olist-Redis-W2!q9` |
| Không còn bản rõ | Không tệp nào trong thư mục bài chứa một trong ba mật khẩu ở dạng rõ |
| Kết quả | `/etc/olist-shop/secrets.env` `0640 root:olist` có `DATABASE_PASSWORD=...` và `REDIS_PASSWORD=...` (worker-2 dùng mật khẩu Redis riêng) |
| Không lộ | Output của `ansible-playbook --diff -v` (lần đầu, và khi xoay mật khẩu database bằng `-e vault_olist_db_password=...`) không chứa mật khẩu nào |
| Idempotent | Chạy lại `changed=0` |
| Sai mật khẩu | Chạy với mật khẩu vault sai thì playbook fail (`Decryption failed`), không in bí mật |

Mã hoá trên máy bạn (không cần lab, không kết nối máy nào):

```bash
cd tracks/devops/modules/09-config-management/exercises/intermediate/02-vault-secrets/starter &&
ansible-vault encrypt --vault-id prod@prompt inventory/group_vars/workers/vault.yml &&
ansible-vault encrypt_string --vault-id prod@prompt --name vault_olist_redis_password
```

`prod@prompt` hỏi mật khẩu trên terminal. Lệnh cuối đọc giá trị từ stdin: gõ giá trị rồi Ctrl-D **hai lần** (không Enter, nếu không
dấu xuống dòng thành một phần của mật khẩu), chép khối `!vault |` vào `host_vars/worker-2.yml`.

**Cách test chấm.** Test ghi mật khẩu vault vào tệp tạm `0600` rồi truyền `--vault-id prod@<tệp>`. `AnsibleLab` dựng `worker-1`,
`worker-2`; chạy `ansible-vault view`, playbook lần đầu với `--diff -v`, lần hai, lần xoay mật khẩu, và lần sai mật khẩu. Khoảng
15 giây.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao tách `vars.yml` và `vault.yml` (grep thấy tên biến, review được thay đổi, chỉ tệp vault là nhị phân).
- Nói được `no_log` và `diff: false` chặn gì, và chỗ nào bí mật vẫn có thể lộ (`-vvv` của module khác, `debug`, tệp trên máy đích,
  callback ghi log).
- Mô tả được quy trình xoay mật khẩu vault (`ansible-vault rekey`) và mật khẩu ứng dụng, ai cần làm gì.

## Gợi ý

### Gợi ý 1

Một tệp vault có thể chứa nhiều biến. Đặt tiền tố `vault_` cho biến trong tệp vault rồi trỏ biến thường sang nó là quy ước trong tài
liệu Ansible ("best practices"). `ansible-vault view` và `ansible-vault edit` không để lại bản rõ trên đĩa.

### Gợi ý 2

Task ghi tệp chứa bí mật cần cả `no_log: true` (che kết quả task, kể cả với `-v`) và `diff: false` (không in khác biệt nội dung khi
chạy `--diff`). Kiểm bằng cách chạy test với starter: output có mật khẩu ở dòng nào.
