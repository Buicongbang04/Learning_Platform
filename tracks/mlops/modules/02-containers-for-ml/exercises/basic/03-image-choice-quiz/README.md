---
title: Chọn base image, layer và cách giao model cho image ML
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn đúng base image, thứ tự layer và cách giao model cho một service ML, thay vì copy Dockerfile từ lần trước.

## Đề bài

Bài này không có code. Làm 6 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): slim hay full hay alpine, vì sao sửa một dòng code lại cài lại dependency, đóng model vào image hay mount ngoài, việc nào thật sự làm image nhỏ đi, vì sao không chạy bằng root, và image cho cả CPU lẫn GPU NVIDIA.

Trước khi chọn, tự hỏi: ràng buộc nào quyết định (kích thước, tốc độ build, khả năng rollback, bảo mật)? Phương án này đổi lấy cái gì?

## Tiêu chí đạt

- Trả lời đúng ít nhất 5/6 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Loại trừ trước: phương án nào chỉ đúng trong một điều kiện hẹp mà câu hỏi không nêu?

### Gợi ý 2

Với mỗi phương án còn lại, nói được nó đổi lấy cái gì (kích thước, tốc độ build, rollback, bảo mật).
