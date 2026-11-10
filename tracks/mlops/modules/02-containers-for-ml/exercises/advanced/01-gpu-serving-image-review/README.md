---
title: Review Dockerfile và Compose GPU cho service embedding
level: advanced
services: []
files:
  - path: starter/Dockerfile
    note: Dockerfile do đồng nghiệp viết, cần review
  - path: starter/compose.gpu.yaml
    note: Compose triển khai lên máy GPU
  - path: starter/REVIEW.md
    note: Bài làm của bạn
run: []
---

## Mục tiêu

Đọc hiểu một Dockerfile và Compose dùng CUDA, tìm lỗi vận hành và đề xuất bản sửa kèm đường lui chạy được trên máy chỉ có CPU.

## Đề bài

Đội muốn đưa service embedding (PyTorch, 1 GPU) lên máy trạm có card NVIDIA. Đồng nghiệp gửi `starter/Dockerfile` và `starter/compose.gpu.yaml`. Máy dev của cả đội không có GPU (chỉ CPU). Bạn không cần chạy chúng (máy có thể không có GPU); đọc và viết `starter/REVIEW.md` theo mẫu có sẵn:

1. **Findings**: ít nhất 6 vấn đề, mỗi vấn đề có mức độ (blocker / nên sửa / tuỳ chọn), vì sao nguy hiểm trong vận hành, và cách sửa cụ thể.
2. **Đường CPU**: thiết kế để cùng một mã nguồn build và chạy được cho CPU (dev, CI) và GPU (production) mà không nhân đôi Dockerfile.
3. **Kích thước và cache**: ước lượng thứ gì chiếm dung lượng (CUDA runtime, torch) và cách giữ layer nặng không bị build lại.
4. **Điều kiện tiên quyết trên host**: driver, NVIDIA Container Toolkit, cách kiểm bằng một lệnh.
5. **Bản Dockerfile sửa** (khối code trong REVIEW.md).

## Tiêu chí đạt

- Mỗi mục 1 đến 5 có nội dung cụ thể, không chung chung.
- Có ít nhất một phát hiện về base image, một về user, một về cách khai báo GPU trong Compose, một về ghim phiên bản.
- Tự chấm theo rubric trong `SOLUTION.md` sau khi làm xong.

## Gợi ý

### Gợi ý 1

Phân biệt image `runtime` và `devel`, và việc driver nằm ở host hay trong image.

### Gợi ý 2

Compose khai báo GPU qua `deploy.resources.reservations.devices`; thử nghĩ điều gì xảy ra khi máy không có toolkit.
