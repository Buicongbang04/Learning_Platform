---
title: Đọc Terraform mẫu cho ML - resource nào tốn tiền khi rảnh và lệnh dọn
level: intermediate
services: []
files:
  - path: main.tf
    note: Terraform mẫu cho một lab SageMaker, chỉ đọc
run: []
---

## Mục tiêu

Đọc một tệp Terraform cho hạ tầng ML mà không chạy nó: chỉ ra resource nào tính tiền khi nhàn rỗi, đoán được cái gì chiếm hoá đơn, và biết lệnh xem trước và dọn đúng cách. Mục tiêu là **đọc hiểu** để review IaC của đồng nghiệp hay dọn một lab; viết Terraform thành thạo thuộc module DevOps.

## Đề bài

Bài này không chạy `terraform` (máy học không cài sẵn, và bài không cần tài khoản cloud). Mở `main.tf` (khoảng 110 dòng, một lab SageMaker kiểu AWS: bucket, ECR, role, notebook, model, endpoint, NAT, budget), đọc từng khối, rồi làm 8 câu trắc nghiệm trong app (card **Trắc nghiệm**): hai câu về resource tính tiền khi rảnh, hai câu về lệnh `terraform` để xem trước và liệt kê, và bốn câu về dọn dẹp, tag, ngân sách và phần bị bỏ sót.

Trước khi chọn, với mỗi resource tự hỏi: nó tính tiền theo giờ, theo dung lượng hay theo lần dùng; nó có sống khi không ai gọi; và ai (hay lệnh nào) xoá nó.

## Tiêu chí đạt

- Trả lời đúng ít nhất 7/8 câu.
- Với mỗi câu sai, nói lại được điều kiện làm cho đáp án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Chia resource thành ba nhóm: khai báo (model, endpoint_config, role: không tính tiền), lưu trữ (bucket, ECR: tính theo dung lượng, rẻ), và chạy theo giờ (endpoint, notebook, NAT: tính tiền chừng nào còn tồn tại). Chỉ nhóm thứ ba làm hoá đơn nhảy khi bạn quên.

### Gợi ý 2

Nhân giá giờ với số instance và 730 giờ/tháng cho từng resource chạy theo giờ; con số cho thấy thứ bạn cần cảnh giác nhất.
