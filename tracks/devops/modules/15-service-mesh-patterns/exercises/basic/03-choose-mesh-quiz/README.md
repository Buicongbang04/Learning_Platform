---
title: Trắc nghiệm - có cần mesh không, chọn mesh nào, chọn pattern nào
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Ra quyết định như người làm platform: khi nào service mesh đáng tiền, chọn Linkerd, Istio, Consul hay Cilium theo ràng buộc của tổ
chức, và chọn đúng cloud design pattern cho một triệu chứng cụ thể.

## Đề bài

Bài này không có code. Làm 12 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 10 câu chọn một đáp án, 2 câu chọn mọi đáp án
đúng. Đọc mục 1 tới 7 của module trước khi làm.

Với mỗi câu, tự hỏi:

1. **Vấn đề thật là gì?** Bảo mật giữa service, độ tin cậy khi gọi nhau, quan sát, hay chỉ là tải?
2. **Ai vận hành?** Bao nhiêu người platform, đã quen proxy nào, có ngân sách RAM không?
3. **Phạm vi?** Chỉ Kubernetes, hay có VM, nhiều cluster?
4. **Mesh có giải được không?** Có thứ mesh không làm được (nghiệp vụ, idempotency, dữ liệu).

## Tiêu chí đạt

- Đúng ít nhất 10/12 câu.
- Với mỗi câu sai, nói lại được vì sao đáp án đúng đúng, và tình huống nào thì phương án bạn chọn mới hợp.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Mesh giải ba nhóm việc ở tầng mạng: danh tính và mã hoá (mTLS), độ tin cậy khi gọi nhau (retry, timeout, chia traffic), quan sát theo
cặp service. Nó không biết nghiệp vụ của bạn và luôn tốn RAM, độ trễ, công vận hành.

### Gợi ý 2

Retry ở nhiều tầng thì số lần thử nhân với nhau, không cộng. Pattern nhóm Availability xử lý lỗi và quá tải; Data Management xử lý dữ
liệu phân tán; Design & Implementation là cách cắt và nối service; Management & Monitoring là cấu hình và theo dõi.
