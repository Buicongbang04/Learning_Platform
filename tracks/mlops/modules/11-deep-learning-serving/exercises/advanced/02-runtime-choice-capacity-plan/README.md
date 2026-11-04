---
title: Chọn runtime (ONNX Runtime, Triton, TensorRT) và lập kế hoạch dung lượng
level: advanced
services: []
files:
  - path: starter/DECISION.md
    note: Mẫu tài liệu quyết định
run: []
---

## Mục tiêu

Viết tài liệu quyết định mà một tech lead MLOps sẽ viết trước khi đưa model ảnh lên production: chọn runtime và precision cho từng luồng sử dụng, tính số GPU cần, và nói rõ khi nào quyết định phải xem lại. Mọi lập luận dựa trên số đo của chính bạn, không dựa trên benchmark quảng cáo.

## Đề bài

Công ty có model SegFormer-b0 phân đoạn thú cưng (model của bài Advanced 01 hoặc model tí hon nếu bạn chưa fine-tune). Ba luồng dùng:

| Luồng | Tải | Yêu cầu |
| --- | --- | --- |
| App di động "khoe thú cưng" | trung bình 15 req/s, đỉnh 250 req/s trong 2 phút sau mỗi push | p95 < 300 ms; lỗi < 0.1% |
| Batch đêm tạo ảnh đại diện | 2 triệu ảnh mỗi đêm | xong trong 4 giờ, chi phí thấp nhất |
| Công cụ gán nhãn nội bộ | 5 người dùng | người gán nhãn bấm vào con vật là có mask; chất lượng viền quan trọng hơn tốc độ |

Phần cứng: dev có laptop RTX 3050 4 GB; production có thể thuê GPU T4 16 GB hoặc L4 24 GB theo giờ, hoặc chạy CPU 16 vCPU. Docker production **có** NVIDIA runtime (khác máy dev).

Điền `starter/DECISION.md`:

1. Bảng so sánh ONNX Runtime + FastAPI, Triton Inference Server (dynamic batching, nhiều model, metrics), TensorRT (engine build theo GPU và dải shape, FP16/INT8), và ít nhất một phương án khác, theo các tiêu chí: hiệu năng, độ phức tạp vận hành, khả năng tái lập build, hỗ trợ CPU, kỹ năng đội cần.
2. Quyết định runtime, precision, cấu hình batching và phần cứng cho **từng** luồng, có lý do.
3. Kế hoạch dung lượng cho luồng app di động và batch đêm: từ throughput đo được trên máy bạn (harness bài Basic 02, ghi rõ máy và batch size) suy ra số GPU/CPU cần, có hệ số an toàn và giải thích cách quy đổi từ card 3050 sang T4/L4 (và độ không chắc của quy đổi đó).
4. Câu hỏi riêng: nhóm gán nhãn muốn dùng SAM 2 thay SegFormer cho công cụ gán nhãn. Trả lời có hay không, với số liệu về kích thước model và bộ nhớ, và chạy ở đâu.
5. Rủi ro (ít nhất ba, kèm cách kiểm) và điều kiện xem lại quyết định.

## Tiêu chí đạt

- Chấm theo rubric trong `SOLUTION.md`; không có test tự động.
- Mọi con số hiệu năng có nguồn: số đo của bạn (kèm cấu hình) hoặc tài liệu chính thức (kèm link).
- Có ít nhất một chỗ bạn chọn phương án **đơn giản hơn** dù phương án phức tạp nhanh hơn, và giải thích vì sao.

## Gợi ý

### Gợi ý 1

Luồng batch đêm không có yêu cầu latency: batch lớn nhất vừa bộ nhớ, throughput mỗi đô la là thước đo. Luồng di động bị chi phối bởi đỉnh, không phải trung bình: tính cho 250 req/s, rồi hỏi có nên giữ máy cho đỉnh 2 phút hay chấp nhận xếp hàng.

### Gợi ý 2

TensorRT engine gắn với kiến trúc GPU, phiên bản TensorRT và dải shape lúc build; Triton có thể chạy ONNX Runtime backend với TensorRT EP. Tách "server" (Triton hay FastAPI) khỏi "runtime" (ONNX Runtime, TensorRT) khi so sánh.
