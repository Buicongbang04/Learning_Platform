# Lời giải: chọn stack serving

## Hướng làm

Không có đáp án duy nhất. Bài chấm ở chỗ mỗi quyết định gắn với một ràng buộc và một con số.

## Bảng so sánh gợi ý

| Tiêu chí | FastAPI tự viết | BentoML | Triton | Ray Serve |
| --- | --- | --- | --- | --- |
| Thông lượng, độ trễ | Tốt cho CPU nhỏ; overhead Python vài ms | Tương đương, thêm lớp khung | Thấp nhất trên GPU, C++ lõi | Tốt, overhead của Ray |
| Batching | Tự viết | Có batching thích ứng | Dynamic batching mạnh, cấu hình sẵn | Có `@serve.batch` |
| Đa model, pipeline | Tự ghép | Runner và service | Ensemble, backend khác nhau | Đồ thị triển khai, mạnh nhất |
| GPU | Làm được, tự quản bộ nhớ | Làm được | Tối ưu nhất, nhiều model trên một GPU | Làm được, chia phần GPU |
| Vận hành | Ít nhất | Vừa | Cao: repo model, định dạng, cấu hình | Cao: cụm Ray |
| Rủi ro dự án | Không | Nhà cung cấp một | Ổn định, NVIDIA | Anyscale/Ray, cập nhật nhanh |

## Quyết định hợp lý

**A: FastAPI tự viết** (checklist của module này) trong container, 3 replica CPU. Lý do: 200 rps với model vài ms là
một service nhỏ; mọi công cụ khác thêm thứ để vận hành mà không cứu được điểm nghẽn nào. Đổi ý khi số model hoặc đội
dùng chung tăng (khi đó BentoML để chuẩn hoá đóng gói) hoặc khi cần batching mà thông lượng không đạt.

**B: Triton** (hoặc BentoML nếu đội chưa muốn đổi sang ONNX/TorchScript). Một lần dự đoán ~25 ms trên GPU ở batch 1, batch 8 mất
~60 ms: dynamic batching với độ trễ hàng đợi tối đa 20 ms cho ~8 ảnh mỗi 80 ms, tức ~100 ảnh/giây trên một GPU; 50 rps đỉnh vừa đủ
một GPU và cần GPU thứ hai để dự phòng. Điều kiện đổi ý: nếu không có ai giữ được định dạng và cấu hình Triton, dùng BentoML với batching thích ứng và chấp nhận thông lượng thấp hơn.

**C: Ray Serve** nếu đã có Ray hoặc đồ thị sẽ phức tạp thêm; nếu không, **FastAPI tự viết + hai service model + một gateway** chạy trên K8s với HPA. Ước lượng
CPU: 1 500 rps x 20 ms = 30 lõi-giây mỗi giây; mức sử dụng 60% nên cần 50 lõi, tức khoảng 13 replica 4 lõi, thêm 30%
dư cho đỉnh và một replica lỗi: ~17. Với p95 80 ms, độ trễ của ba bước cộng lại phải nằm dưới ngân sách (embedding 25, xếp hạng 25, luật 5, mạng 15). Đội 3 người thường chọn phương án sau trừ khi nhu cầu đồ thị rõ.

## Chi phí vận hành

Một người sở hữu nền tảng serving, runbook rollback chung (alias + reload), dashboard RED chung. Nợ chấp nhận: tự duy trì
mã batching ở A (nhỏ); định dạng model riêng ở B.

## Kế hoạch đo

k6 `constant-arrival-rate` ở 100% và 150% tải đỉnh, warmup tách riêng, ngưỡng p95 theo SLO, kiểm `dropped_iterations`
bằng 0 và `checks` trên nội dung. Đo lại sau mỗi thay đổi cấu hình batch.

## Rubric (tối đa 20 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Bảng so sánh ≥4 phương án theo cùng tiêu chí, có đánh đổi thật | 4 |
| Quyết định rõ cho cả ba workload, gắn với ràng buộc | 5 |
| Mỗi quyết định có điều kiện đổi ý đo được | 3 |
| Ước lượng tài nguyên có phép tính (độ trễ, batch, mức sử dụng) | 4 |
| Vận hành: ai trực, tự động gì, nợ kỹ thuật | 2 |
| Kế hoạch đo bằng k6 có ngưỡng và cách đọc | 2 |

Từ 14 điểm trở lên là đạt. Lỗi hay gặp: chọn công cụ nặng nhất cho workload nhỏ; ước lượng GPU mà không tính batching; quên rằng
đội 3 người phải trực.
