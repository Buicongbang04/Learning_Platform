---
title: Chọn chiến lược deploy và rollback theo ràng buộc thật
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn chiến lược deploy (rolling, blue/green, canary, recreate, shadow, feature flag) từ ràng buộc của từng tình huống thay vì
theo thói quen, và biết rollback bằng gì để nhanh và chắc.

## Đề bài

Bài này không có code. Làm 9 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 8 câu chọn một đáp án, câu cuối chọn mọi
đáp án đúng. Các câu đi qua: thay đổi logic rủi ro trên API stateless, đổi giao thức buộc mọi thành phần đổi cùng lúc, worker giữ
khoá độc quyền, tách ngày deploy khỏi ngày ra mắt, đổi tên cột không downtime, rollback nhanh nhất, đọc kết quả canary theo
ngưỡng, thử service viết lại bằng traffic thật, và điều kiện để rolling update không rớt request.

Trước khi chọn, với mỗi tình huống tự hỏi:

1. Hai phiên bản có được phép cùng nhận traffic hay cùng chạy trong một lúc không?
2. Cần đo bản mới trên traffic thật trước khi cho mọi người dùng, hay cần đổi một lần cho tất cả?
3. Có dư tài nguyên để chạy song song hai bộ đầy đủ không? Dữ liệu (schema, hàng đợi) có tương thích với cả hai bản không?

## Tiêu chí đạt

- Trả lời đúng ít nhất 7/9 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định và điều kiện để phương án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Rolling và canary đều có lúc hai phiên bản cùng phục vụ; blue/green chỉ có một bản nhận traffic tại một thời điểm nhưng cần gấp
đôi tài nguyên; recreate chấp nhận downtime ngắn để tránh hai bản chạy song song. Feature flag tách "deploy code" khỏi "bật tính
năng", không thay chiến lược deploy.

### Gợi ý 2

Rollback nhanh nhất là thứ không phải build lại: một artifact đã có sẵn, đã chạy tốt, định danh không đổi được. Một quyết định
canary tốt đã được viết ra **trước** khi canary chạy.
