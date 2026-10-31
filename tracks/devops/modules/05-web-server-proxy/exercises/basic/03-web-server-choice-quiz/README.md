---
title: Chọn web server, proxy và load balancer theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn đúng loại thành phần (web server, servlet container, reverse proxy, forward proxy, L4 hay L7 load balancer) và đúng
sản phẩm (Nginx, Caddy, Apache, Tomcat, IIS, HAProxy, Envoy) từ ràng buộc thật, thay vì dùng Nginx cho mọi thứ.

## Đề bài

Bài này không có code. Làm 9 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 8 câu chọn một đáp án, câu cuối
chọn mọi đáp án đúng. Các câu đi qua: forward và reverse proxy, L4 và L7, HTTPS tự động, ứng dụng Java `.war`, hosting chia
sẻ, service mesh, phân biệt 502 và 504, passive health check, và Nginx đứng sau load balancer cloud.

Trước khi chọn, với mỗi tình huống tự hỏi:

1. Lưu lượng là gì (HTTP hay TCP thuần), và thành phần này cần đọc tới tầng nào?
2. Ai cấu hình nó, bao lâu đổi một lần, có được reload không?
3. Nó đứng ở phía client (đi ra) hay phía server (đi vào)?

## Tiêu chí đạt

- Trả lời đúng ít nhất 7/9 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định và điều kiện để phương án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Forward proxy đại diện cho client (client biết và cấu hình nó), reverse proxy đại diện cho server (client không biết nó
tồn tại). L4 chỉ thấy IP và cổng, L7 đọc được HTTP.

### Gợi ý 2

502 là Nginx không nói chuyện được với upstream (từ chối kết nối, đóng kết nối, response hỏng); 504 là upstream nhận
nhưng không trả lời kịp. Nginx open source chỉ có passive health check.
