---
title: Inventory tĩnh và playbook đầu tiên cho ba máy Olist Shop
level: basic
services: []
files:
  - path: starter/inventory/hosts.yml
    note: Inventory YAML, viết nhóm
  - path: starter/inventory/group_vars/all.yml
    note: Biến chung, đã có sẵn
  - path: starter/site.yml
    note: Play chưa có task
  - path: starter/templates/host.ini.j2
    note: Template Jinja2 mới có hai dòng
  - path: tests/test_first_playbook.py
    note: Không sửa
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/09-config-management/exercises/basic/01-inventory-first-playbook -q -rs
---

## Mục tiêu

Mô tả một nhóm máy bằng inventory YAML có nhóm lồng nhau, đặt biến đúng tầng (`group_vars`, `host_vars`), viết một play chỉ dùng
module có trạng thái và một template Jinja2, rồi chứng minh play idempotent: chạy lại không đổi gì, `--check --diff` sạch.

## Đề bài

Olist Shop staging có ba máy: `web-1` chạy API, `worker-1` và `worker-2` chạy worker. Viết inventory trong `starter/inventory/`
và play trong `starter/site.yml`.

**Inventory** (`inventory/hosts.yml`, định dạng YAML)

| Mục | Yêu cầu test kiểm (đọc bằng `ansible-inventory -i inventory --list`) |
| --- | --- |
| Nhóm | `web` có `web-1`; `workers` có `worker-1`, `worker-2`; `olist` có đúng hai nhóm con `web` và `workers`, không liệt kê host trực tiếp |
| Biến chung | `olist_env: staging` cho mọi máy (`group_vars/all.yml`, đã có) |
| Biến nhóm | `olist_role: web` cho nhóm `web`; `olist_role: worker` và `olist_worker_concurrency: 2` cho nhóm `workers`; máy web không có `olist_worker_concurrency` |
| Biến máy | `worker-2` có `olist_worker_concurrency: 4` (đặt trong `inventory/host_vars/worker-2.yml`) |
| Kết nối | `hosts.yml` không chứa biến `ansible_*` nào: lab tự cấp địa chỉ, cổng, user |

**Play** (`site.yml`, nhắm nhóm `olist`)

| Mục | Yêu cầu |
| --- | --- |
| Group, user | Group hệ thống `olist`; user hệ thống `olist` (UID dưới 1000) có group chính là `olist`, shell `/usr/sbin/nologin`, home `/var/lib/olist-shop` nhưng **không** tạo thư mục home |
| Thư mục | `/etc/olist-shop`, quyền `0755`, `root:root` |
| Tệp | `/etc/olist-shop/host.ini` từ `templates/host.ini.j2`, quyền `0644`, `root:root`, nội dung đúng từng byte như bảng dưới |
| Cách viết | Chỉ module có trạng thái: không `shell`, `command`, `raw`, `script` |

Nội dung `host.ini` mong đợi (dòng `concurrency` chỉ có ở worker, tệp kết thúc bằng một dấu xuống dòng):

```ini
[host]
name = worker-2
env = staging
role = worker
concurrency = 4
```

```ini
[host]
name = web-1
env = staging
role = web
```

**Cách test chấm.** `AnsibleLab` dựng ba container SSH tên `web-1`, `worker-1`, `worker-2` (target thật, không phải máy bạn) rồi
chạy trong sandbox: `ansible-inventory --list`, `ansible-playbook site.yml` hai lần, rồi `--check --diff`. Inventory kết nối do lab
sinh được truyền sau inventory của bạn. Cả bài khoảng 20 giây (lần đầu build image target lâu hơn, cần mạng cho `apt`).

## Tiêu chí đạt

- `ansible-inventory` cho đúng nhóm và biến như bảng; biến `olist_worker_concurrency` của `worker-2` là 4, của `worker-1` là 2.
- Lần chạy đầu thành công trên cả ba máy, có thay đổi; `host.ini`, thư mục, user đúng như bảng.
- Lần chạy thứ hai `changed=0` trên mọi máy; `--check --diff` sau đó cũng `changed=0`.
- Giải thích được vì sao `group_vars` đặt cạnh inventory (`inventory/group_vars/`) và cạnh playbook đều được đọc, và cái nào thắng.

## Gợi ý

### Gợi ý 1

Trong YAML inventory, nhóm con nằm dưới khoá `children`, host nằm dưới `hosts` với giá trị rỗng (`worker-1:`). Kiểm cây nhóm bằng
`ansible-inventory -i inventory --graph` và biến của một máy bằng `ansible-inventory -i inventory --host worker-2`; hai lệnh này
không kết nối tới máy nào nên chạy được ngay trên máy bạn.

### Gợi ý 2

`ansible.builtin.template` mặc định bật `trim_blocks`, nên dòng chỉ chứa `{% if ... %}` hay `{% endif %}` không để lại dòng trống.
`ansible.builtin.user` có `system: true`, `create_home: false`, `shell`, `home`, `group`. Tạo group trước user.
