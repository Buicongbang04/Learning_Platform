---
title: Inventory động từ CMDB, constructed và host pattern cho rollout canary
level: intermediate
services: []
files:
  - path: starter/inventory/cmdb.py
    note: Script inventory, mới trả inventory rỗng
  - path: starter/inventory/constructed.yml
    note: Plugin constructed, chưa có nhóm
  - path: starter/rollout.yml
    note: Hai play, sửa host pattern
  - path: tests/fixtures/cmdb.json
    note: Bản export CMDB mẫu
  - path: tests/fixtures/cmdb-messy.json
    note: Bản export có dữ liệu bẩn
  - path: tests/test_dynamic_inventory.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/09-config-management/exercises/intermediate/03-dynamic-inventory -q -rs
---

## Mục tiêu

Sinh inventory từ nguồn sự thật bên ngoài (CMDB, API cloud) thay vì sửa tay tệp hosts, chuẩn hoá dữ liệu bẩn, gom nhóm thêm bằng
plugin `constructed`, và chọn đúng máy cho từng đợt rollout bằng host pattern.

## Đề bài

Team hạ tầng xuất danh sách máy từ CMDB mỗi đêm ra JSON (`tests/fixtures/cmdb.json`): mỗi máy có `name`, `ip`, `role`, `env`, `az`,
`status`, `cpu`, `canary`. Viết inventory động trong `starter/inventory/` (thư mục này là nguồn inventory, Ansible đọc mọi tệp trong
đó theo thứ tự tên).

**`inventory/cmdb.py`** (Python, chỉ thư viện chuẩn, có quyền thực thi, dòng đầu `#!/usr/bin/env python3`)

| Mục | Yêu cầu |
| --- | --- |
| Nguồn | Đọc tệp JSON ở đường dẫn trong biến môi trường `OLIST_CMDB_FILE`; thiếu biến hay không đọc được tệp thì in lỗi có chữ `OLIST_CMDB_FILE` ra stderr và thoát mã khác 0 (không bao giờ trả inventory rỗng: playbook sẽ chạy "thành công" trên 0 máy) |
| Giao thức | `--list` in JSON inventory có `_meta.hostvars`; `--host <tên>` in `{}` |
| Lọc | Chỉ máy có `status` là `active` (không phân biệt hoa thường) |
| Nhóm | `role_<role>`, `env_<env>`, `az_<az>`: chữ thường, mọi ký tự không phải chữ hay số thành `_` (`Payment-API` thành `role_payment_api`, `hcm-1a` thành `az_hcm_1a`); máy thiếu `az` không vào nhóm `az_*` nào |
| Biến máy | `ansible_host` (= `ip`), `olist_role`, `olist_env`, `olist_az` (chữ thường, hay `null` khi thiếu), `olist_cpu` (số), `olist_canary` (bool, mặc định `false`) |

**`inventory/constructed.yml`**: plugin `ansible.builtin.constructed`, `strict: true`; nhóm `canary` (máy có `olist_canary`), nhóm
`big` (`olist_cpu` từ 8); biến `olist_worker_concurrency` bằng `olist_cpu * 2`.

**`rollout.yml`**: giữ hai play và tên của chúng; play 1 chỉ nhắm worker prod là canary, play 2 nhắm worker prod **không** phải
canary. Dùng host pattern (giao `:&`, loại `:!`), không liệt kê tên máy.

Bài này chỉ chạy `ansible-inventory` và `ansible-playbook --list-hosts`, không kết nối máy nào, nên `ansible_host` được phép.

**Cách test chấm.** Chạy trong sandbox `ansible-inventory -i inventory/cmdb.py --list` (riêng script) và `-i inventory` (script
cộng constructed) với `OLIST_CMDB_FILE` trỏ tới từng fixture, chạy thẳng `cmdb.py --host` và `cmdb.py --list` khi thiếu biến, rồi
`ansible-playbook -i inventory rollout.yml --list-hosts`. Vài giây.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao script inventory trả `_meta` (một lần gọi thay vì một lần mỗi máy).
- Nói được khi nào dùng script, khi nào dùng inventory plugin (`amazon.aws.aws_ec2`, `constructed`), và cache inventory để làm gì.
- Viết được pattern cho: mọi máy prod ở `hcm-1a` trừ database.

## Gợi ý

### Gợi ý 1

`re.sub(r"[^a-z0-9]+", "_", value.lower())` chuẩn hoá tên nhóm. In JSON bằng `json.dumps`. Thử từng bước:
`OLIST_CMDB_FILE=$PWD/../tests/fixtures/cmdb.json ansible-inventory -i inventory --graph` trong thư mục `starter/`.

### Gợi ý 2

Trong `constructed`, `groups:` nhận biểu thức Jinja2 trả bool, `compose:` nhận biểu thức trả giá trị. `strict: true` làm biểu thức
lỗi (biến không tồn tại) thành lỗi thật thay vì bị bỏ qua. Pattern `role_worker:&env_prod:!canary` đọc là: thuộc `role_worker`, và
thuộc `env_prod`, và không thuộc `canary`.
