---
title: Quyết định tự dựng hay dùng dịch vụ cloud ML cho một case, có số liệu
level: advanced
services: []
files:
  - path: starter/DECISION.md
    note: Khung quyết định, điền mọi TODO
  - path: tests/fixtures/DECISION.bad.md
    note: Ví dụ quyết định yếu, test dùng để kiểm bộ kiểm tra
  - path: tests/test_decision.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/advanced/02-build-vs-cloud-service -q
---

## Mục tiêu

Chọn giữa tự dựng nền tảng (MLflow, orchestrator, serving trên Kubernetes), dùng dịch vụ cloud ML (SageMaker, Vertex AI hay Azure ML) hoặc lai, và **bảo vệ được lựa chọn bằng số**: ma trận có trọng số, chi phí 24 tháng, điểm hoà vốn và điều kiện đổi hướng. Câu trả lời đúng phụ thuộc case; điểm của bài là lý luận có số liệu nhất quán.

## Đề bài

Case: startup logistics có 4 người ML, đã có 2 model chạy production (dự báo nhu cầu, ước tính thời gian giao) và dự kiến lên **10 model trong 12 tháng**. Toàn bộ dữ liệu đã nằm trên một cloud lớn; một kỹ sư nền tảng dành khoảng 50% thời gian cho ML; không có yêu cầu pháp lý đặc biệt nhưng khách hàng doanh nghiệp hỏi về nơi lưu dữ liệu; tải đỉnh khoảng 30 request/giây, p95 dưới 200 ms; ngân sách hạ tầng ML bị soi mỗi quý.

Viết `starter/DECISION.md`, giữ các heading `## 1.` tới `## 6.`, không còn chữ `TODO`. Ba phương án luôn là `Tự dựng`, `Cloud`, `Lai` (ví dụ MLflow tự host cộng serving trên dịch vụ cloud).

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và giả định | Ít nhất 300 ký tự văn xuôi (không tính bảng) |
| 2. Ma trận tiêu chí | Bảng cột `Tiêu chí`, `Trọng số`, `Tự dựng`, `Cloud`, `Lai`; ít nhất 6 tiêu chí, trong đó có tiêu chí chứa `chi phí` và tiêu chí chứa `vận hành`; trọng số là số nguyên cộng bằng 100; điểm là số nguyên 1 đến 5; dòng cuối `Tổng có trọng số` có tổng = Σ(trọng số × điểm) / 100 làm tròn 2 chữ số, khớp từng cột |
| 3. Chi phí 24 tháng | Bảng cột `Hạng mục`, `Tự dựng`, `Cloud`, `Lai` có ba dòng `Chi phí một lần`, `Chi phí mỗi tháng`, `Tổng 24 tháng` (số USD), với tổng = một lần + 24 × mỗi tháng; cộng một dòng văn xuôi `Điểm hoà vốn` nêu tháng (số nguyên) mà `Tự dựng` rẻ hơn `Cloud` tính theo hai cột đó (sai lệch tối đa 1 tháng), hoặc nói `không có` khi không bao giờ hoà vốn |
| 4. Khuyến nghị | Một dòng `**Khuyến nghị:**` kèm đúng một trong `Tự dựng`, `Cloud`, `Lai`; nếu phương án đó **không** có tổng điểm cao nhất ở phần 2 thì phải có cụm `lệch khỏi điểm số` và giải thích |
| 5. Điều kiện đổi hướng | Ít nhất 3 gạch đầu dòng, mỗi dòng có một con số cụ thể (số model, tháng, tiền, độ trễ) |
| 6. Rủi ro | Ít nhất 3 gạch đầu dòng, có nhắc `lock-in` |

Test chỉ kiểm khung và tính nhất quán số học ở trên; một test khác đưa một quyết định yếu vào cùng bộ kiểm tra và đòi nó bị bắt. Nội dung chấm bằng rubric trong `solutions/advanced/02-build-vs-cloud-service/SOLUTION.md`; đọc rubric **sau** khi viết xong. Giá trong bài là con số bạn tự ước và phải ghi giả định ở phần 1; khi áp dụng thật dùng bảng giá hiện hành (bài ước tính chi phí ở mức Basic có thể làm bảng tính).

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/advanced/02-build-vs-cloud-service -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Mỗi điểm số ở phần 2 truy được về một dữ kiện trong đề; trọng số phản ánh ràng buộc của **case này**, không phải sở thích.
- Khuyến nghị nêu điều gì làm nó đổi (phần 5) bằng ngưỡng có số.

## Gợi ý

### Gợi ý 1

Chi phí nhân công vận hành thường lớn hơn hoá đơn hạ tầng ở đội nhỏ: tính giờ của kỹ sư nền tảng theo giá thật của họ, không coi bằng 0. Cũng đừng quên chi phí một lần của việc chuyển sang dịch vụ cloud (viết lại pipeline theo SDK của họ).

### Gợi ý 2

Trọng số đặt trước khi chấm điểm, để điểm không bị kéo về phương án bạn thích. Nếu phương án có điểm cao nhất lại không phải thứ bạn khuyến nghị, đó thường là dấu hiệu trọng số hay điểm chưa phản ánh đúng ràng buộc; sửa ma trận hoặc nói rõ vì sao lệch.
