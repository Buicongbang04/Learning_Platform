---
title: Viết lại playbook toàn shell bằng module, changed_when và failed_when
level: basic
services: []
files:
  - path: starter/harden.yml
    note: Playbook cũ toàn shell, viết lại
  - path: starter/inventory/hosts.yml
    note: Ba worker, không sửa
  - path: tests/test_modules_not_shell.py
    note: Không sửa
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/09-config-management/exercises/basic/02-modules-not-shell -q -rs
---

## Mục tiêu

Thấy tận mắt vì sao `shell` phá idempotency (dòng lặp, `changed` mỗi lần chạy, mã thoát bị hiểu sai), viết lại bằng module có
trạng thái, và dùng `changed_when`/`failed_when` đúng chỗ cho những lệnh chỉ đọc.

## Đề bài

`starter/harden.yml` là playbook một người viết từ script bash cũ. Chạy lần đầu trên `worker-1` (log sạch) nó fail ở bước đếm lỗi;
chạy lần hai thì `worker.env` có hai dòng `LOG_LEVEL`. Viết lại toàn bộ.

Trước khi chạy, test tạo trên mỗi máy `/etc/olist-shop/worker.env`:

```text
DATABASE_HOST=db.internal
TZ=UTC
```

và tệp log `/var/log/olist-shop/worker.log`: `worker-1` có 3 dòng không có `ERROR`; `worker-2` có 7 dòng `ERROR`; `worker-3`
**không có** tệp log.

| Việc | Yêu cầu test kiểm |
| --- | --- |
| Thư mục | `/opt/olist-shop/releases` quyền `0750` `root:root`; có thư mục `/opt/olist-shop/releases/1.4.2` |
| Symlink | `/opt/olist-shop/current` là symlink tới `/opt/olist-shop/releases/1.4.2` |
| Env file | Trên `worker-1`, `worker.env` đúng từng byte `DATABASE_HOST=db.internal`, `TZ=Asia/Ho_Chi_Minh`, `LOG_LEVEL=INFO` (mỗi dòng một, theo thứ tự đó): dòng `TZ` được sửa tại chỗ, `LOG_LEVEL` thêm một lần duy nhất |
| Kiểm Python | Một task `ansible.builtin.command` đọc `python3 --version`; play dừng nếu nhỏ hơn 3.12 |
| Đếm lỗi | Một task `ansible.builtin.command` chạy `grep -c ERROR /var/log/olist-shop/worker.log`. Không có dòng nào khớp (mã 1) là bình thường; không đọc được tệp (mã 2) là lỗi của **chính task này** |
| Dừng khi lỗi nhiều | Từ 5 dòng `ERROR` trở lên thì máy đó dừng ở một task `ansible.builtin.assert` hoặc `ansible.builtin.fail`, thông báo có chữ `ERROR` và số dòng |
| Cách viết | Không còn `shell`, `raw`, `script`; đúng hai task `ansible.builtin.command` (hai phép kiểm trên), cả hai không bao giờ báo `changed` |

**Cách test chấm.** `AnsibleLab` dựng ba container SSH, tạo tệp như trên, chạy `harden.yml` hai lần. Test đọc kết quả từng task
qua callback của lab: task nào fail trên máy nào, module gì, có `changed` không. Kỳ vọng: `worker-1` không lỗi, lần hai
`changed=0`; `worker-2` dừng ở `assert`/`fail`; `worker-3` dừng ở task đếm. Khoảng 15 giây.

## Tiêu chí đạt

- Mọi test pass. Lần hai trên `worker-1`: `changed=0` và `worker.env` vẫn ba dòng.
- Nói được ba lý do `shell` không idempotent: không biết trạng thái hiện tại, mặc định luôn `changed`, mã thoát khác 0 luôn là fail.
- Phân biệt được `failed_when` (khi nào là lỗi) với `ignore_errors` (lỗi rồi nhưng bỏ qua), và vì sao `ignore_errors` ở đây sai.

## Gợi ý

### Gợi ý 1

`ansible.builtin.lineinfile` với `regexp: "^TZ="` sửa dòng khớp hoặc thêm dòng mới ở cuối nếu không có dòng nào khớp.
`ansible.builtin.file` với `state: link` tạo symlink, `state: directory` tạo thư mục, cả hai so trạng thái trước khi đổi.

### Gợi ý 2

Đăng ký kết quả bằng `register: errors` rồi `failed_when: errors.rc > 1`. Trong `assert`, `errors.stdout | int` là số dòng đếm
được; test so sánh phiên bản bằng `is version("3.12", ">=")`.
