---
title: Build vs buy cho nền tảng ML - Databricks, SageMaker, Vertex AI hay open source
level: advanced
services: []
files:
  - path: starter/DECISION.md
    note: Khung ghi quyết định, điền từng phần
run: []
---

## Mục tiêu

Ra một quyết định build vs buy có thể bảo vệ trước ban lãnh đạo và trước đội kỹ thuật: so phương án bằng tổng chi phí sở hữu (TCO), độ phù
hợp với ràng buộc, rủi ro khoá chặt (lock-in) và năng lực của đội, chứ không bằng danh sách tính năng hay sở thích công cụ.

## Đề bài

Cùng công ty ở bài Advanced 01, nhưng giả sử bạn đứng trước câu hỏi trước khi bắt đầu xây: **giữ và mở rộng stack open source tự vận hành
(MLflow, Kubernetes, KServe, Feast, Kueue như các module 04-16), hay chuyển sang một nền tảng managed?** Dữ kiện:

- Dữ liệu: data lake trên object storage của một cloud lớn, khoảng 400 TB; đội dữ liệu đang dùng Spark tự quản lý và cân nhắc Databricks.
- Ngân sách hạ tầng ML hiện tại khoảng 55 000 USD mỗi tháng (đã tính cụm Kubernetes, GPU, lưu trữ), cụm chạy 30% công suất.
- Đội nền tảng 3 người, lương đầy đủ khoảng 15 000 USD mỗi người mỗi tháng; tuyển thêm mất 4-6 tháng.
- Ràng buộc: dữ liệu thẻ của đội fraud thuộc phạm vi PCI DSS; một khách hàng doanh nghiệp đòi dữ liệu của họ ở trong một vùng địa lý cố định.
- Đội search cần GPU theo đợt (6 giờ mỗi tuần), đội ads muốn bắt đầu trong tháng này.

So ít nhất bốn phương án: (A) open source tự vận hành như hiện tại, (B) SageMaker hoặc Vertex AI theo cloud đang dùng, (C) Databricks
(cả dữ liệu và ML), (D) lai: managed cho huấn luyện và notebook, tự vận hành serving và quy ước. Điền `starter/DECISION.md` (tối đa 4
trang): ma trận tiêu chí có trọng số, ước tính TCO 3 năm cho từng phương án (ghi rõ giả định), rủi ro lock-in và cách giảm, kế hoạch di
chuyển, và điều kiện khiến bạn đổi quyết định.

Giá dịch vụ cloud thay đổi liên tục: dùng bảng giá công khai tại thời điểm bạn làm bài và ghi ngày tra; rubric chấm lập luận, không chấm
con số tuyệt đối. Không có test tự động: tự chấm bằng rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Đạt ít nhất 70/100 điểm rubric.
- TCO tính cả chi phí con người (vận hành, trực, nâng cấp) và chi phí di chuyển, không chỉ hoá đơn cloud.
- Có ít nhất ba điều kiện cụ thể (có số hoặc sự kiện) khiến bạn xem lại quyết định.

## Gợi ý

### Gợi ý 1

Chi phí ẩn lớn nhất của tự vận hành là thời gian người: nâng cấp Kubernetes và KServe, vá CVE, trực đêm. Chi phí ẩn lớn nhất của managed là
phí cộng thêm trên compute (thường tính theo giờ instance cao hơn compute thường) và chi phí rời đi.

### Gợi ý 2

Quyết định hiếm khi là tất cả hay không có gì. Tách nền tảng thành lớp (lưu trữ, huấn luyện, registry, serving, quy ước và cổng) và hỏi riêng
từng lớp: lớp này có phải lợi thế cạnh tranh của công ty không, và đội có đủ người để trực nó không.
