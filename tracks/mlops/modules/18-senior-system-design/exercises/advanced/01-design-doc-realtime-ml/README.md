---
title: Design doc cho ML realtime - fraud hoặc ETA ở quy mô lớn
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung design doc, điền mọi TODO
  - path: tests/fixtures/DESIGN.bad.md
    note: Ví dụ design doc yếu, test dùng để kiểm bộ kiểm tra
  - path: tests/test_design_doc.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/advanced/01-design-doc-realtime-ml -q
---

## Mục tiêu

Viết một design doc mà đội khác review được: yêu cầu có số, SLO đo đúng chỗ, phương án bị loại có lý do, ước tính dung lượng, chế độ
hỏng và cách rollout. Đây là sản phẩm chính của một kỹ sư senior trước khi viết dòng code nào. Chọn **một** trong hai đề.

## Đề bài

**Đề fraud: chấm điểm gian lận realtime cho ví điện tử.** 30 triệu người dùng, trung bình 800, đỉnh 4 000 giao dịch mỗi giây. Quyết định
cho qua, chặn hay đòi OTP phải trả trong 150 ms p99. Gian lận chiếm 0.08% giao dịch; người dùng báo cáo sau 1-3 ngày, chargeback về sau
30-90 ngày. Hiện dùng bộ luật tĩnh bắt khoảng 55% giá trị gian lận và chặn nhầm 0.9% giao dịch hợp lệ. Các đợt tấn công thường kéo dài vài
phút, nên cần đếm giao dịch theo tài khoản, thiết bị, merchant trong cửa sổ 1 phút và 1 giờ.

**Đề eta: ETA cho app gọi xe ở 3 thành phố.** Đỉnh 1 200 yêu cầu mỗi giây, p99 dưới 120 ms. Nhãn (thời gian thật) về khi chuyến kết
thúc, sau 10-60 phút. Tốc độ theo từng đoạn đường được tính mỗi phút từ GPS tài xế đi qua Kafka. Model hiện tại là GBM huấn luyện hằng
tuần; giờ cao điểm và mưa làm sai số tăng gấp đôi. Đội sản phẩm muốn thêm thành phố thứ tư trong 3 tháng.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 8.`, không còn chữ `TODO`. Luật mà test kiểm:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| Đầu tệp | Dòng `Đề: fraud` hoặc `Đề: eta` |
| 1. Bối cảnh, yêu cầu và ngoài phạm vi | Bảng cột `Yêu cầu`, `Con số` có ít nhất 5 dòng mà ô `Con số` chứa chữ số; có cụm `ngoài phạm vi` và ít nhất 2 gạch đầu dòng |
| 2. SLO | Bảng cột `SLI`, `Đo ở đâu`, `SLO`, `Cửa sổ`; ít nhất 4 dòng không ô trống; cột `SLI` có một dòng nhắc `chất lượng` và một dòng nhắc `freshness` hoặc `độ tươi` |
| 3. Kiến trúc | Khối ` ```mermaid ` có ít nhất 8 cạnh (`-->`, `-.->` hoặc `==>`); ít nhất 200 ký tự giải thích ngoài bảng và sơ đồ |
| 4. Phương án và đánh đổi | Bảng cột `Phương án`, `Chi phí`, `Độ trễ`, `Chất lượng`, `Chọn`; ít nhất 3 phương án; đúng một dòng có `Chọn` là `có` |
| 5. Ước tính dung lượng và chi phí | Ít nhất 3 gạch đầu dòng có chữ số |
| 6. Chế độ hỏng | Bảng cột `Hỏng`, `Phát hiện`, `Giảm thiểu`; ít nhất 5 dòng không ô trống; có chữ `fallback` |
| 7. Rollout và rollback | Ít nhất 3 gạch đầu dòng; có `shadow` hoặc `canary`, và `rollback` |
| 8. Câu hỏi cho design review | Ít nhất 6 gạch đầu dòng kết thúc bằng `?` |

Test chỉ kiểm khung; một test khác đưa một design doc yếu vào cùng bộ kiểm tra và đòi nó bị bắt. Nội dung chấm bằng rubric trong
`solutions/advanced/01-design-doc-realtime-ml/SOLUTION.md`; đọc rubric **sau** khi viết xong. Tốt nhất là nhờ một người khác review
doc của bạn bằng chính các câu hỏi ở phần 8 trước khi tự chấm.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/advanced/01-design-doc-realtime-ml -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric của đề đã chọn.
- Mỗi con số ở phần 5 truy được về một yêu cầu ở phần 1; mỗi SLO ở phần 2 nói rõ đo ở điểm nào và vì sao điểm đó gần người dùng.

## Gợi ý

### Gợi ý 1

Bắt đầu bằng khung trả lời ở mục 6 của README module: yêu cầu, chỉ số, dữ liệu và nhãn, baseline, kiến trúc online và offline, serving,
đánh giá, vận hành. Viết phần 1 và 2 trước; phần kiến trúc chỉ có nghĩa khi đã biết đo thành công bằng gì.

### Gợi ý 2

Với mỗi hộp trong sơ đồ, hỏi "nó chết thì sao". Câu trả lời là một dòng ở phần 6. Nếu câu trả lời là "thanh toán dừng" hoặc "app không có
ETA", bạn còn thiếu một fallback.
