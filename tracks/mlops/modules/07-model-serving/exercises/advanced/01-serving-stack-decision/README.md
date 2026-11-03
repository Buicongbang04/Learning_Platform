---
title: Chọn stack serving cho ba workload khác nhau
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Bản quyết định của bạn
run: []
---

## Mục tiêu

Chọn công cụ serving bằng tiêu chí và số liệu cho từng workload, nêu điều kiện khiến bạn đổi ý, thay vì chọn cái quen tay.

## Đề bài

Công ty có một đội nền tảng 3 người. Ba workload cần serving:

- **A, ETA taxi:** LightGBM/sklearn, 200 request/giây đỉnh, p95 dưới 150 ms, CPU, một model, retrain hằng đêm.
- **B, phân đoạn ảnh:** PyTorch, 50 request/giây đỉnh, p95 dưới 120 ms, một GPU 12 GB, ảnh 512x512, batch tăng thông lượng rõ rệt.
- **C, gợi ý:** pipeline ba bước (embedding, xếp hạng, luật nghiệp vụ), 1 500 request/giây đỉnh, p95 dưới 80 ms, hai model nhỏ và một bước luật, cần co giãn theo giờ cao điểm.

Viết `starter/DESIGN.md` gồm:

1. **Bảng so sánh** ít nhất bốn phương án (FastAPI tự viết, BentoML, Triton, Ray Serve; được thêm TorchServe hoặc KServe) theo cùng tiêu chí: thông lượng/độ trễ, batching, đa model, GPU, độ phức tạp vận hành, rủi ro dự án (bảo trì, khoá nhà cung cấp).
2. **Quyết định cho từng workload** (A, B, C): một phương án chính, một lý do đo được, một điều kiện đổi ý.
3. **Ước lượng tài nguyên** cho B và C: số replica hoặc GPU, và cách bạn đi tới con số đó (độ trễ một lần dự đoán, kích thước batch, mức sử dụng mục tiêu).
4. **Chi phí vận hành**: ai trực, cái gì tự động, bạn chấp nhận nợ kỹ thuật nào.
5. **Kế hoạch đo**: kịch bản k6 nào chứng minh quyết định đúng, ngưỡng và cách đọc.

## Tiêu chí đạt

- Mỗi workload có quyết định rõ, không "tuỳ tình huống".
- Số liệu ước lượng có phép tính (vd. 1 500 rps x 20 ms CPU mỗi request / mức sử dụng 60% / số lõi mỗi replica).
- Tự chấm theo rubric trong `SOLUTION.md` sau khi làm xong.

## Gợi ý

### Gợi ý 1

Bắt đầu từ ràng buộc quyết định của từng workload (GPU? đồ thị nhiều bước? đội 3 người?), loại phương án vượt khả năng vận hành, rồi mới so điểm mạnh.

### Gợi ý 2

Phương án nhàm chán thường thắng: hỏi "tôi có thật sự đang tự viết lại batching, hay đây chỉ là một service nhỏ?".
