---
title: Chọn công cụ theo tình huống trên bản đồ roadmap
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Luyện phản xạ của một DevOps engineer khi được hỏi "dùng công cụ gì": bắt đầu từ ràng buộc (quy mô team, ngân sách,
ai vận hành, yêu cầu an ninh, hệ sinh thái sẵn có), không bắt đầu từ công cụ đang hot. Đồng thời làm quen bản đồ
công cụ của cả lộ trình trước khi đi vào từng module.

## Đề bài

Bài này không có code. Làm 12 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới). Mỗi câu là một tình huống
thật-dạng thuộc một nhóm công cụ của roadmap: CI/CD, configuration management, provisioning, secret management,
logs management, container orchestration, serverless, web server, artifact management, GitOps, service mesh,
application monitoring.

Với mỗi câu, trước khi chọn hãy tự trả lời bốn câu hỏi ở phần 6 của lý thuyết:

1. Ai sẽ vận hành công cụ này lúc 3 giờ sáng, và họ đã biết nó chưa?
2. Ràng buộc cứng là gì (không cài agent, phải on-prem, ngân sách, mã nguồn mở)?
3. Công cụ có khớp hệ sinh thái đang có không (GitHub, Grafana, Kubernetes)?
4. Quy mô hiện tại cần gì, và 12 tháng tới cần gì?

Nộp xong, đọc lời giải: mỗi câu giải thích vì sao đáp án đúng, khi nào các phương án còn lại lại là lựa chọn đúng.

## Tiêu chí đạt

- Trả lời đúng ít nhất 10/12 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định trong tình huống và điều kiện để phương án bạn chọn trở
  thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Đáp án "mạnh nhất" hiếm khi là đáp án đúng. Công cụ đúng là công cụ nhỏ nhất thoả ràng buộc cứng mà team vận hành
được. Mỗi thành phần mới là thêm một thứ phải nâng cấp, vá lỗi, trực on-call.

### Gợi ý 2

Đọc kỹ chữ trong tình huống: "không cho cài agent", "nhiều backend", "ngân sách gần bằng 0", "không ai muốn trực
server", "review được diff theo từng key". Mỗi câu có đúng một chi tiết loại bỏ được hai phương án.
