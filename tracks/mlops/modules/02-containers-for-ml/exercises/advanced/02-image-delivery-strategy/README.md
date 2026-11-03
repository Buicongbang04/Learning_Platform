---
title: Chiến lược giao hình ảnh và model cho dịch vụ ETA
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Bản thiết kế của bạn
run: []
---

## Mục tiêu

Quyết định có kèm đánh đổi: đóng model vào image hay mount ngoài, cách đặt tag, quét lỗ hổng và dọn registry cho một dịch vụ có nhịp retrain hằng ngày.

## Đề bài

Dịch vụ ETA taxi (xem capstone): model sklearn khoảng 30 MB, retrain hằng đêm, đổi code vài lần mỗi tuần; image khoảng 500 MB; chạy 6 replica trên 3 máy; có môi trường staging và production; kiểm toán yêu cầu truy được "tháng 3 dịch vụ trả ETA bằng model nào, image nào". Viết `starter/DESIGN.md` gồm:

1. **Quyết định chính**: model trong image hay ngoài image (volume, object storage), có so sánh ít nhất ba phương án (model trong image; model mount từ volume; model tải từ registry khi khởi động) theo cùng các tiêu chí: tốc độ rollout, rollback, tái lập, điểm hỏng lúc khởi động, kích thước registry.
2. **Chiến lược tag**: tag nào mutable, tag nào immutable, có dùng digest không, quan hệ giữa image tag, version model và git commit.
3. **Quét lỗ hổng**: trivy chạy ở đâu (PR, build, định kỳ), chính sách chặn (mức nào, bản vá chưa có thì sao), ai xử lý ngoại lệ và ngoại lệ hết hạn thế nào.
4. **Dọn dẹp và chi phí**: giữ bao nhiêu image, bao nhiêu bản model, điều gì không được xoá.
5. **Kế hoạch lỗi**: model mới hỏng lúc 3 giờ sáng, bạn rollback thế nào và mất bao lâu.

## Tiêu chí đạt

- Chọn một phương án rõ ràng và nêu điều kiện khiến bạn đổi ý.
- Số liệu ước lượng cụ thể (băng thông, dung lượng registry sau 90 ngày, thời gian rollout).
- Tự chấm theo rubric trong `SOLUTION.md` sau khi làm xong.

## Gợi ý

### Gợi ý 1

Tính dung lượng registry sau 90 ngày với hai phương án trước khi chọn; lớp dependency được dùng lại giữa các image.

### Gợi ý 2

Hỏi: lúc kiểm toán, từ một request trong log, đường nào dẫn tới model và dữ liệu huấn luyện?
