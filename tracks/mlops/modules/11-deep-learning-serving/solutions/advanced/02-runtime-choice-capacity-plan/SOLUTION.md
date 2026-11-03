# Hướng làm và rubric: chọn runtime và kế hoạch dung lượng

## Hướng làm

- **Tách server và runtime.** Triton là server (HTTP/gRPC, dynamic batching, nhiều model, metrics Prometheus, model repository); ONNX Runtime và TensorRT là runtime. Triton có thể chạy backend ONNX Runtime (kèm TensorRT EP), TensorRT, PyTorch. So "Triton vs ONNX Runtime" là so nhầm tầng.
- **App di động**: một model, một GPU nhỏ, đội đã viết batcher: ONNX Runtime CUDA FP16 sau FastAPI là đủ và dễ debug. Triton đáng giá khi có nhiều model chung GPU, cần gRPC, hoặc muốn dynamic batching và metrics có sẵn mà không tự viết. Tính dung lượng cho đỉnh: nếu một T4 đạt X ảnh/giây ở batch 8 với p95 trong ngân sách, cần `ceil(250 / (0.6 X))` GPU (hệ số 0.6 cho headroom và quy đổi), hoặc ít hơn nếu chấp nhận hàng đợi ngắn trong 2 phút đỉnh và có load shedding.
- **Batch đêm**: 2 triệu ảnh trong 4 giờ là khoảng 139 ảnh/giây. Không cần latency, nên batch lớn nhất vừa bộ nhớ, FP16 hoặc INT8, có thể TensorRT engine vì shape cố định và lợi ích throughput lớn; so chi phí GPU theo giờ với CPU nhiều lõi chạy INT8. Job idempotent, checkpoint theo shard, chạy trên instance spot.
- **Công cụ gán nhãn**: 5 người, chất lượng viền quan trọng: input độ phân giải cao hơn, FP32, batch 1, có thể chỉ một GPU nhỏ dùng chung hoặc CPU.
- **SAM 2**: model nhỏ nhất (Hiera tiny) khoảng 39 triệu tham số, bản large khoảng 224 triệu; image encoder chạy ở 1024×1024, nặng hơn SegFormer-b0 (3.7 triệu tham số) hàng chục lần và bản lớn không thoải mái trên 4 GB khi xử lý video. Hợp lý cho công cụ gán nhãn chạy trên GPU production (T4/L4) vì tương tác bằng điểm bấm giúp người gán nhãn nhanh hơn và mask của nó có thể làm nhãn để fine-tune SegFormer; không hợp lý cho luồng di động. Câu trả lời tốt nói rõ SAM 2 là công cụ **tạo nhãn**, không thay model serving.
- **Quy đổi 3050 sang T4/L4**: không có hệ số chính xác (băng thông bộ nhớ, số Tensor Core, clock, nhiệt laptop khác nhau); dùng số đo trên 3050 để chọn cấu hình, rồi đo lại một giờ trên card thuê trước khi chốt số lượng.
- **Rủi ro**: engine TensorRT build trên máy khác GPU không chạy; OOM khi đổi độ phân giải; FP16 làm lệch mask ở lớp viền; driver/CUDA production khác dev; cold start tải model lớn. Mỗi rủi ro một cách kiểm (verify trong CI trên đúng loại GPU, test OOM với burst, so mask FP16 và FP32 trên tập val, pin phiên bản, đo thời gian khởi động).

## Rubric

| Tiêu chí | 0 điểm | 1 điểm | 2 điểm |
| --- | --- | --- | --- |
| So sánh runtime | Liệt kê tên | Có bảng tiêu chí | Tách server và runtime, đúng về TensorRT engine và Triton backend |
| Quyết định từng luồng | Một cấu hình cho cả ba | Mỗi luồng một cấu hình | Có lý do gắn với yêu cầu từng luồng |
| Dung lượng | Không có số | Có phép tính | Từ số đo của mình, có headroom và nói rõ độ không chắc khi quy đổi card |
| SAM 2 | Không trả lời | Có/không chung chung | Có số tham số/bộ nhớ, đặt đúng vai trò (gán nhãn) và nơi chạy |
| Rủi ro | Không có | Liệt kê | Mỗi rủi ro có cách kiểm cụ thể |
| Đơn giản có chủ đích | Không có | Có nhắc | Chỉ ra chỗ chọn phương án đơn giản hơn với lý do vận hành |

Đạt từ 8/12 điểm.
