# Lời giải: trắc nghiệm configuration management

| Câu | Đáp án | Giải thích ngắn |
| --- | --- | --- |
| precedence-role-vars | b | Role `vars` (tầng 15) cao hơn `inventory/group_vars/workers.yml` (tầng 6). Biến người dùng cần ghi đè đặt ở `defaults` (tầng 2). Đây chính là sự cố ở Intermediate 04 |
| precedence-extra-vars | c | Extra vars luôn thắng, kể cả `set_fact`; vì vậy `-e` hợp cho tham số một lần (bản deploy) và nguy hiểm khi dùng để "sửa nhanh" biến cấu hình |
| shell-idempotency | a | `shell` không biết trạng thái; `lineinfile` với `regexp` có. Recap `changed` mỗi lần làm mất tín hiệu thay đổi thật |
| grep-failed-when | d | Mã 1 của grep là "không khớp"; `failed_when` định nghĩa lỗi đúng, `changed_when: false` vì lệnh chỉ đọc. `ignore_errors` nuốt cả lỗi thật |
| handler-timing | b | Handler chạy cuối play hoặc ở `meta: flush_handlers`; `force_handlers` không đổi thời điểm |
| handler-failure | c | Máy fail bị loại khỏi play, handler đang chờ của nó không chạy; `force_handlers` buộc chạy. Không có nó, lần sau tệp đã đúng nên không ai notify nữa: service chạy cấu hình cũ |
| check-diff | a | Check mode không đổi gì, nhưng chỉ đúng với module hỗ trợ; `command`/`shell` bị bỏ qua (trừ khi có `creates`/`removes`), task sau phụ thuộc kết quả của chúng có thể sai |
| vault-practice | b | Tách `vars.yml` (tên biến grep được) và `vault.yml` (mã hoá), vault id theo môi trường, `no_log` cho task dùng bí mật |
| serial-rollout | d | `serial` chia đợt, `max_fail_percentage: 0` dừng khi có lỗi. `strategy: free` không dừng gì; `run_once` chỉ chạy một máy |
| push-pull | a | Máy tự kéo cấu hình khi boot là pull. Tốt hơn nữa là không phải cấu hình gì khi boot: image dựng sẵn |
| mutable-immutable | c | Stateless, scale nhanh, cần giống hệt: image bất biến; role Ansible vẫn dùng làm provisioner của Packer |
| tool-choice | b | Agent, catalog khai báo, chạy định kỳ tự sửa drift, báo cáo tập trung: Puppet (hay Chef, Salt). cloud-init chỉ chạy lúc boot đầu |
| roles-defaults | c | `defaults` thấp nhất (giao diện của role), `vars` cao (hằng số nội bộ, ví dụ đường dẫn theo distro) |
| idempotence-tests | a, b, d | Converge hai lần và `--check` sau converge bắt được hành vi; `ansible-lint` bắt mẫu xấu tĩnh. `--syntax-check` chỉ kiểm cú pháp |
