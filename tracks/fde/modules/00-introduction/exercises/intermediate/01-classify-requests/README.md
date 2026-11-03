---
title: Sáu yêu cầu của khách, bốn trụ
level: intermediate
services: []
files:
  - path: starter/requests.yaml
    note: Điền 6 yêu cầu
  - path: tests/test_requests.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/00-introduction/exercises/intermediate/01-classify-requests -q
---

## Mục tiêu

Nghe một câu khách nói và nhận ra **việc thật** nằm sau nó: cài đặt tại hiện trường, làm việc với khách, thiết kế hệ
thống hay cloud. Nhận sai loại việc là nguồn gốc của phần lớn tuần lãng phí đầu tiên ở khách: viết code khi khách cần
một con số ROI, hay họp scope khi máy khách đang hỏng cert.

## Đề bài

Sáu câu dưới đây là nguyên văn khách gửi trong tuần đầu của các dự án khác nhau:

| Id | Khách nói |
| --- | --- |
| `r1` | IT bệnh viện: "Hôm qua anh cài ở máy test thì chạy, nhưng trên máy chủ ở viện, `pip install` trong container báo `CERTIFICATE_VERIFY_FAILED`. Máy đã ra internet qua proxy của viện rồi mà." |
| `r2` | COO công ty logistics: "Trước khi ký mở rộng, tôi cần biết hệ thống này tiết kiệm được bao nhiêu giờ công mỗi tháng so với cách đội tôi đang làm." |
| `r3` | Trưởng phòng pháp chế: "Luật sư bên tôi sợ trợ lý trả lời sai mà nghe rất tự tin. Làm sao tôi biết nó không bịa trước khi mở cho 40 người dùng?" |
| `r4` | Giám đốc khối: "Thêm giúp tôi so sánh hợp đồng với mẫu chuẩn, xuất Excel và đăng nhập bằng tài khoản Google, tất cả trước buổi demo với HĐQT thứ Sáu tuần sau." |
| `r5` | CTO tập đoàn: "Năm sau chúng tôi muốn mở cho 5 công ty con, mỗi nơi chỉ thấy tài liệu của mình, tổng khoảng 2 triệu tài liệu. Kiến trúc sẽ thế nào, chỗ nào nghẽn trước?" |
| `r6` | Trưởng phòng cloud: "Chúng tôi muốn hệ thống chạy trong tài khoản AWS của chính chúng tôi. Bên anh không được giữ quyền admin lâu dài; mọi truy cập phải qua role chúng tôi cấp và thu hồi được." |

Điền `starter/requests.yaml`, mỗi yêu cầu một mục với bốn trường:

- `pillar`: trụ của track chứa **việc chính** bạn phải làm để đáp yêu cầu đó, một trong `field` (trụ 1, module 01–10),
  `customer` (trụ 2, module 11–14), `design` (trụ 3, DSA và System Design: module 15–18 và 20), `cloud` (trụ 4: module
  19 và Cloud lab `c1`–`c3`). Bảng bốn trụ ở phần 4 của lý thuyết và bảng module ở [README của track](../../../../../README.md).
- `module`: id module (đúng như trong `tracks/fde/track.json`, vd. `05-gpu-field`) dạy việc chính đó; phải thuộc trụ bạn chọn.
- `why`: vì sao đây là việc chính, không phải việc khác nghe có vẻ giống (ít nhất 30 ký tự).
- `first_step`: việc **đầu tiên, cụ thể** bạn làm trong 24 giờ tới (ít nhất 30 ký tự, khác `why`, mỗi yêu cầu một câu riêng).

Có câu nghe như một loại việc nhưng thực ra là loại khác; đọc kỹ khách **cần gì để ra quyết định**, không chỉ từ khoá
trong câu.

## Tiêu chí đạt

- Có đúng sáu mục `r1`…`r6` dưới khoá `requests`.
- `pillar` thuộc `field`, `customer`, `design`, `cloud`; `module` có trong `track.json` và thuộc đúng dải module của trụ đã chọn.
- `why` và `first_step` mỗi trường ít nhất 30 ký tự, không còn `TODO`, khác nhau trong cùng mục; sáu `first_step` khác nhau.
- `pillar` của từng yêu cầu đúng với đáp án; `module` là một trong các module dạy việc chính đó (có yêu cầu chấp nhận hơn
  một module, vd. vừa thuộc module chuyên đề vừa thuộc module xử lý sự cố).

## Gợi ý

### Gợi ý 1

Hỏi: "Nếu tôi làm xong việc này, khách sẽ làm được gì mà hôm nay chưa làm được?" Câu trả lời là quyết định ký, một
máy chạy được, một bản thiết kế, hay một mô hình quyền trên cloud.

### Gợi ý 2

Một câu hỏi về độ tin cậy của câu trả lời AI cần **bằng chứng đo được** trên dữ liệu của khách, không chỉ một cuộc nói
chuyện thuyết phục. Xem module nào của trụ 1 dạy cách đo.

### Gợi ý 3

Ba tính năng cộng một hạn chót cứng: việc đầu tiên không phải là code tính năng nhanh nhất, mà là biết buổi demo cần
chứng minh điều gì.
