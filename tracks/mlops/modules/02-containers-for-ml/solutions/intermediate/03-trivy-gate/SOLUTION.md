# Lời giải: trivy gate

## Dockerfile

`trivy config` báo ba finding trên starter (và `FROM python:3.12` đáng ghim tag đầy đủ, `slim`, dù trivy không bắt):

| ID | Mức | Sửa |
| --- | --- | --- |
| DS-0002 | HIGH | Có `USER` không phải root |
| DS-0005 | LOW | `COPY` thay `ADD` (ADD tự giải nén và tải URL, hành vi khó đoán) |
| DS-0026 | LOW | Thêm `HEALTHCHECK` |

(Danh sách chính xác phụ thuộc bản trivy và bộ check; đọc `Title` và `Message` của từng finding.) Ghim `flask==3.1.2` cho cài đặt tái lập.

## `gate()`

Xem `triage.py`. Quyết định thiết kế:

- Chỉ mức trong `fail_on` được xét; còn lại không xuất hiện ở đâu cả.
- `ignore_unfixed` là **chính sách**, không phải chi tiết kỹ thuật: lỗ hổng chưa có bản vá thì chặn deploy cũng không sửa được, nhưng phải còn thấy trong `ignored` để theo dõi, và bật nó là một quyết định cần người chịu trách nhiệm.
- `allow` (allowlist) nên có lý do và ngày hết hạn ở nơi lưu policy; hàm chỉ thực thi.
- Một CVE có thể xuất hiện ở nhiều target (OS, Python); phải khử trùng, và nếu ở target này đã có bản vá còn target kia thì không thì vẫn blocking.
- Trivy ghi `"Vulnerabilities": null` hoặc bỏ khoá khi không có gì: xử lý bằng `or []`.
