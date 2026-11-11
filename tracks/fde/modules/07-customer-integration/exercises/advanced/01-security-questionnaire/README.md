---
title: "Trả lời security questionnaire của công ty luật"
level: advanced
services: []
files:
  - path: starter/questionnaire.md
    note: 12 câu hỏi của phòng An toàn thông tin; bạn trả lời ngay trong tệp
run: []
---

## Mục tiêu

Trước khi ký mở rộng từ thử nghiệm lên toàn công ty, phòng An toàn thông tin của công ty luật gửi bộ câu hỏi đánh giá
nhà cung cấp. Sales muốn "trả lời Có hết cho nhanh". Bạn là người duy nhất biết sản phẩm chạy thế nào ở máy khách, và
câu trả lời của bạn sẽ thành cam kết trong phụ lục hợp đồng. Việc của bạn: trả lời **đúng sự thật**, có bằng chứng khách
tự kiểm được, chia rõ trách nhiệm, và với chỗ sản phẩm còn thiếu thì nói thẳng kèm biện pháp bù và kế hoạch.

## Đề bài

Trả lời 12 câu trong `starter/questionnaire.md` cho quillo 1.0.0 như đang triển khai ở công ty luật (compose trên một
máy Ubuntu, SSO qua Keycloak của khách, ACL theo thư mục, connector file share, export CSV từ hệ thống cũ). Nguồn sự thật
là sản phẩm: [README sản phẩm](../../../../../product/README.md), mã trong `tracks/fde/product/src/quillo/`,
`compose.yaml`, `compose.sso.yaml`, `.env.example`, `REQUIREMENTS.yaml`, và những gì bạn đã làm ở các bài trước của
module. Mỗi câu theo đúng khung trong tệp (Trả lời / Chi tiết / Bằng chứng / Trách nhiệm), tổng không quá ~1 500 từ.
Không có test tự động; tự chấm (hoặc nhờ người khác chấm) theo rubric dưới đây, bài mẫu và rubric chi tiết ở
`solutions/`.

## Tiêu chí đạt

Rubric 20 điểm, đạt khi ≥ 15 và **không** có lỗi loại trừ:

| Tiêu chí | Điểm |
| --- | --- |
| Đúng sự thật với sản phẩm: mọi "Có" có thật trong code/cấu hình; chỗ thiếu ghi "Không"/"Một phần" | 6 |
| Bằng chứng khách tự kiểm được (tệp, biến cấu hình, lệnh `curl`/`docker`/`ss`…) ở ít nhất 8/12 câu | 4 |
| Trách nhiệm chia rõ vendor/khách/chung (vd. mã hoá đĩa, MFA, giữ log, xoay secret) | 3 |
| Mỗi chỗ thiếu có biện pháp bù hiện có và hướng xử lý (cấu hình, quy trình, yêu cầu gửi product) | 4 |
| Viết cho người đọc là chuyên viên bảo mật: ngắn, cụ thể, không quảng cáo, không thuật ngữ mơ hồ ("bảo mật cấp ngân hàng") | 3 |

Lỗi loại trừ (một lỗi là không đạt): khẳng định sản phẩm tự mã hoá dữ liệu at rest; nói không có tài khoản/token tĩnh
nào; nói log không bao giờ chứa dữ liệu cá nhân; hứa xoá từng tài liệu qua API ở bản 1.0.0; hứa một SLA vá lỗi hay chứng
nhận (ISO 27001, SOC 2, pentest) mà bạn không có bằng chứng.

## Gợi ý

### Gợi ý 1

Với mỗi câu, tự hỏi "khách kiểm câu trả lời này bằng lệnh gì?". Không nghĩ ra lệnh nào thì câu trả lời đang là lời hứa,
không phải sự thật.

### Gợi ý 2

Đi theo dữ liệu: một hợp đồng từ file share tới inbox, `done/`, database, prompt của LLM, câu trả lời, log. Mỗi chặng
lưu gì, ở đâu, bao lâu?

### Gợi ý 3

Tách "sản phẩm làm" khỏi "triển khai ở khách làm" khỏi "khách phải làm". Questionnaire hay bị trả lời sai nhất ở chỗ
nhập nhằng ba thứ đó.
