---
title: Chọn công nghệ bằng ma trận quyết định có trọng số và phân tích độ nhạy
level: advanced
services: []
files:
  - path: starter/decision_matrix.py
    note: 5 hàm TODO (ma trận, xếp hạng, độ nhạy)
  - path: starter/matrix.yaml
    note: Ma trận của bạn cho bài toán dưới đây
  - path: starter/decision.md
    note: Văn bản quyết định 7 mục
  - path: tests/test_decision.py
    note: Không sửa; chỉ kiểm hợp đồng tối thiểu
run:
  - uv run pytest tracks/data-engineer/modules/00-introduction/exercises/advanced/01-technology-decision-matrix -q
  - uv run python tracks/data-engineer/modules/00-introduction/exercises/advanced/01-technology-decision-matrix/starter/decision_matrix.py
---

## Mục tiêu

Ra một quyết định công nghệ mà người khác phản biện được: ước lượng khối lượng từ số đo thật, viết tiêu chí và
trọng số ra giấy, chấm điểm, rồi **kiểm tra độ nhạy** xem quyết định có đứng vững khi trọng số lệch đi một chút
không. Đây là bài "chọn công nghệ" mà phần 7 lý thuyết của module nhắc tới.

## Đề bài

**Bài toán.** Sở Tài nguyên và Môi trường TP.HCM lắp **300 trạm** cảm biến khí giá rẻ, mỗi trạm đo cùng các chỉ số
như bộ UCI Air Quality nhưng **mỗi phút một lần**. Yêu cầu:

- cảnh báo khi CO hoặc NO2 vượt ngưỡng **trong vòng 5 phút**, và khi một trạm im lặng quá 15 phút;
- dashboard công khai cập nhật **hằng giờ**; báo cáo tháng cho lãnh đạo;
- đội: **2 Data Engineer, 1 analyst**, không có SRE trực đêm; ngân sách vận hành hạn chế;
- dữ liệu quan trắc môi trường phải lưu **trong lãnh thổ Việt Nam** (hạ tầng tự host hoặc cloud trong nước).

Việc cần làm:

1. `starter/decision_matrix.py`: `validate`, `weighted_scores`, `rank`, `reweight` (đổi trọng số một tiêu chí,
   các tiêu chí khác co giãn theo tỉ lệ cũ) và `flip_point` (trọng số gần nhất làm phương án đứng đầu đổi).
   Test kiểm bằng ví dụ ma trận trong phần 7 lý thuyết và một phép quét vét cạn.
2. `starter/matrix.yaml`: ước lượng khối lượng (`bytes_per_reading` lấy từ số đo thật của bộ UCI ở bài basic 03 hoặc
   intermediate 02), ít nhất 3 phương án (gợi ý: một máy với MQTT + TimescaleDB; Kafka + Flink + ClickHouse;
   một dịch vụ IoT managed), ít nhất 5 tiêu chí có trọng số, điểm 1–5, và quyết định.
3. `starter/decision.md`: 7 mục `## Bài toán`, `## Ước lượng khối lượng`, `## Phương án`, `## Tiêu chí và trọng số`,
   `## Ma trận`, `## Độ nhạy`, `## Quyết định`.

## Tiêu chí đạt

- Test pass: điểm ví dụ lý thuyết đúng (4,25 / 4,40 / 3,05), `validate` bắt đủ 4 loại lỗi, `flip_point` khớp phép quét
  vét cạn với sai số 0,002, `matrix.yaml` hợp lệ và `raw_gb_per_year` khớp phép nhân của chính bạn.
- Chọn khác phương án điểm cao nhất thì có `override_reason`.
- `decision.md` giải thích **vì sao** từng trọng số, nêu tiêu chí nhạy nhất và điều kiện để xem lại quyết định.
- Rubric chi tiết trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Khi trọng số của một tiêu chí là w, điểm mỗi phương án là hàm **tuyến tính** theo w. Phương án đứng đầu chỉ đổi tại
giao điểm của hai đường thẳng: tìm bằng công thức, hoặc quét thô rồi chia đôi (bisection) cho tới sai số 1e-3. Nhớ
xét cả hai hướng tăng và giảm.

### Gợi ý 2

300 trạm × 1 440 lần/ngày × ~84 byte (CSV thô của UCI) ≈ 36 MB/ngày, ~13 GB/năm: vừa một máy PostgreSQL. Khi khối
lượng không phải ràng buộc, các tiêu chí quyết định thường là công sức vận hành, năng lực đội và pháp lý.
