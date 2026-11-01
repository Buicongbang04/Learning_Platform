---
title: Rolling update từng máy, health check, rollback và dừng khi lỗi
level: advanced
services: []
files:
  - path: starter/rollout.yml
    note: Playbook deploy cùng lúc mọi máy, viết lại
  - path: starter/inventory/hosts.yml
    note: Ba worker, không sửa
  - path: tests/test_rolling_update.py
    note: Không sửa
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/09-config-management/exercises/advanced/01-rolling-update-serial -q -rs
---

## Mục tiêu

Thiết kế một playbook deploy giới hạn blast radius như ở production: từng máy một, rút khỏi load balancer trước khi đổi, kiểm sức
khoẻ sau khi đổi, tự rollback máy lỗi và dừng cả rollout, không đụng máy đã ở bản đích.

## Đề bài

`starter/rollout.yml` đổi bản worker trên mọi máy cùng lúc và không kiểm gì. Tuần trước bản 1.5.0 lỗi cấu hình làm cả ba worker
chết một lúc. Viết lại theo yêu cầu dưới. Trên mỗi máy, test tạo sẵn:

- `/opt/olist-shop/releases/1.4.2/VERSION` (nội dung `1.4.2`) và symlink `/opt/olist-shop/current` trỏ tới thư mục đó.
- `/usr/local/bin/olist-healthcheck`: in `health: ok <bản>` và thoát 0 khi đọc được `/opt/olist-shop/current/VERSION`; thoát 1 khi có
  tệp `/etc/olist-shop/broken` hoặc không đọc được `VERSION`.
- `worker-2` có `/etc/olist-shop/broken` (máy này sẽ không khoẻ với bất kỳ bản nào cho tới khi tệp bị xoá).

Bản cần deploy truyền bằng `-e olist_release=1.5.0`.

| Yêu cầu | Test kiểm |
| --- | --- |
| Tham số | Thiếu `olist_release` (hay không dạng `X.Y.Z`) thì playbook dừng, không máy nào bị đổi |
| Từng máy | Mỗi đợt một máy, theo thứ tự inventory; một máy lỗi là dừng cả rollout, máy sau không chạy task nào |
| Rút khỏi LB | Trước khi đổi: tạo cờ `/var/lib/olist-shop/maintenance`; máy khoẻ sau khi đổi thì xoá cờ |
| Deploy | Thư mục `/opt/olist-shop/releases/<bản>` có `VERSION` chứa `<bản>`; `current` trỏ sang đó |
| Health | Chạy `/usr/local/bin/olist-healthcheck`, thử lại vài lần (máy thật cần vài giây để lên); không bao giờ báo `changed` |
| Rollback | Máy không khoẻ: `current` trỏ lại bản cũ, **giữ** cờ maintenance (để người trực điều tra trước khi nhận traffic), máy được đánh dấu lỗi với thông báo có chữ `rollback` |
| Idempotent | Máy đã ở bản đích thì không làm gì (không rút khỏi LB): chạy lại sau khi rollout xong `changed=0` |

**Cách test chấm.** `AnsibleLab` dựng `worker-1..3` và tạo trạng thái như trên. Chuỗi: chạy không có `olist_release`; chạy
`1.5.0` (kỳ vọng `worker-1` lên 1.5.0, `worker-2` rollback và giữ cờ, `worker-3` chưa bị đụng, playbook kết thúc lỗi); test xoá
`/etc/olist-shop/broken` rồi chạy lại (cả ba lên 1.5.0, thứ tự từng máy đọc từ callback của lab, `worker-1` `changed=0`); chạy lần
nữa (`changed=0` mọi máy). Khoảng 35 giây.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được `serial`, `max_fail_percentage`, `any_errors_fatal` khác nhau thế nào và chọn cái nào cho tình huống này.
- Nói được vì sao `block`/`rescue` phải kết thúc bằng `fail` ở đây (máy được rescue không bị tính là lỗi).
- Mô tả cách thay cờ maintenance bằng thao tác thật với load balancer (Nginx upstream ở module 05, target group của AWS) và
  `delegate_to` dùng vào đâu ở production (lab cấm `delegate_to` vì không có máy LB).

## Gợi ý

### Gợi ý 1

`ansible.builtin.stat` của symlink có `stat.lnk_source` (đường dẫn đích đã resolve). Ghi nhớ bản cũ bằng `set_fact` trước khi
đổi, đặt khối deploy trong `block` có `when` so bản cũ với bản đích. `until` cùng `retries`, `delay` để thử lại health check.

### Gợi ý 2

Mức play: `serial: 1`, `max_fail_percentage: 0`, `order: inventory`. Kiểm tham số bằng `ansible.builtin.assert` trong `pre_tasks`
với phép thử `is match('^\d+\.\d+\.\d+$')`.
