# Lời giải: Ansible Vault

Mật khẩu vault của lab: `olist-lab-vault-2026` (vault id `prod`). Xem lời giải đã giải mã:

```bash
cd tracks/devops/modules/09-config-management/solutions/intermediate/02-vault-secrets &&
ansible-vault view --vault-id prod@prompt inventory/group_vars/workers/vault.yml
```

## Các quyết định

- **Mã hoá cả tệp cho nhóm, `encrypt_string` cho ngoại lệ.** `vault.yml` của nhóm `workers` mã hoá cả tệp: thêm, bớt bí mật là sửa
  bằng `ansible-vault edit`. Mật khẩu Redis riêng của `worker-2` là một giá trị `!vault` trong `host_vars` thường: tệp vẫn đọc được,
  diff trong PR cho thấy biến nào đổi (dù không thấy giá trị).
- **Tách `vars.yml` và `vault.yml`.** `olist_db_password: "{{ vault_olist_db_password }}"`: grep tên biến thấy nó được định nghĩa ở
  đâu, reviewer biết biến nào là bí mật. Biến `vault_*` của `worker-2` ở `host_vars` thắng biến cùng tên ở `group_vars` (tầng 9 với
  tầng 6), nên chỉ ghi đè đúng một giá trị.
- **Vault id theo môi trường.** `$ANSIBLE_VAULT;1.2;AES256;prod`: CI của staging chỉ có mật khẩu `staging`, không giải mã được tệp
  prod. Chạy nhiều id một lúc: `--vault-id staging@... --vault-id prod@...`.
- **`no_log: true` và `diff: false` trên task ghi bí mật.** Không có chúng, `-v` in kết quả task và `--diff` in nội dung tệp mới:
  test với starter thấy cả ba mật khẩu trong output, tức là trong log CI.
- **Mật khẩu vault ở ngoài repo.** Tệp mật khẩu `0600` do CI ghi từ secret store, hay script `--vault-id prod@vault-client.sh` lấy từ
  secret manager. Không đặt `vault_password_file` trỏ vào repo.

## Xoay vòng

- Mật khẩu vault lộ: `ansible-vault rekey --vault-id prod@old --new-vault-id prod@new` mọi tệp và giá trị `!vault` (giá trị inline
  phải mã hoá lại từng cái), rồi xoay **luôn bí mật bên trong** vì ai có mật khẩu cũ và bản Git cũ vẫn giải mã được lịch sử.
- Mật khẩu ứng dụng: sửa bằng `ansible-vault edit`, deploy, kiểm ứng dụng nối được, rồi thu hồi mật khẩu cũ ở database.

## Đọc thêm

- Vault chỉ bảo vệ bí mật **lúc nằm trong Git**. Trên máy đích tệp `secrets.env` là bản rõ (quyền `0640`), và bất kỳ ai chạy được
  playbook prod đều đọc được. Bí mật động (Vault của HashiCorp, Secrets Manager) cùng lookup lúc chạy hay để ứng dụng tự đọc là bước
  tiếp theo (module 12).
- `-vvv` của vài module vẫn in tham số; `no_log` ở task là chốt chặn cuối, không thay được việc không đưa bí mật qua tham số dòng lệnh.
