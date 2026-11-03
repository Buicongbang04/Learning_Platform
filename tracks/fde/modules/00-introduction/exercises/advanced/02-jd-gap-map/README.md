---
title: Đọc tin tuyển FDE, lập bản đồ khoảng cách của chính bạn
level: advanced
services: []
files:
  - path: starter/gap-map.md
    note: Bảng yêu cầu → bằng chứng → khoảng cách → kế hoạch
run: []
---

## Mục tiêu

Biến "tôi muốn làm FDE" thành một bản đồ cụ thể: nhà tuyển dụng thật sự đòi gì, bạn đã có **bằng chứng** gì cho từng
yêu cầu, thiếu gì, và lấp bằng module, bài tập hay milestone capstone nào của track, trước ngày nào.

## Đề bài

Dưới đây là trích đoạn ba tin tuyển dụng **hư cấu**, viết theo kiểu tin FDE thường gặp ở công ty AI và công ty dữ liệu
(đọc thêm vài tin thật, link ở phần 8 của lý thuyết):

**Công ty A — nền tảng AI cho doanh nghiệp, "Forward Deployed Engineer"**

> Bạn sẽ ngồi cùng khách hàng doanh nghiệp, biến yêu cầu mơ hồ thành hệ thống LLM chạy production trên hạ tầng của họ.
> Viết code Python production, thiết kế pipeline RAG và đánh giá chất lượng, xử lý yêu cầu bảo mật và tuân thủ của khách,
> đi công tác tới 50%. Cần: 4+ năm kinh nghiệm phần mềm, từng làm việc trực tiếp với khách, giao tiếp tốt với cả kỹ sư và
> lãnh đạo, mang phản hồi từ hiện trường về cho đội sản phẩm.

**Công ty B — nền tảng dữ liệu cho ngân hàng, "Forward Deployed Software Engineer, On-prem"**

> Triển khai nền tảng của chúng tôi vào trung tâm dữ liệu của ngân hàng: môi trường air-gapped, Kubernetes do khách quản
> lý, Linux hardening, SSO doanh nghiệp. Tích hợp với kho dữ liệu và hệ thống cũ của khách (SQL, Kafka, SFTP). Chẩn đoán
> sự cố khi chỉ có quyền hạn chế. Cần: Linux, mạng, container, Kubernetes, SQL, một ngôn ngữ backend; kinh nghiệm on-prem
> là điểm cộng lớn.

**Công ty C — startup AI agent, "Founding Forward Deployed Engineer"**

> Bạn là kỹ sư đầu tiên đặt tại khách: tự discovery, chốt scope, dựng prototype full-stack trong vài ngày, đo ROI cùng
> khách và quyết định cái gì được đưa vào sản phẩm. Phỏng vấn gồm coding (cấu trúc dữ liệu và giải thuật), system design,
> một vòng decomposition với bài toán mơ hồ và một vòng nhập vai với khách.

Viết `starter/gap-map.md`:

1. **Yêu cầu chung**: gộp ba tin thành 10–15 yêu cầu (một yêu cầu xuất hiện ở nhiều tin chỉ ghi một lần, ghi tin nào đòi).
2. **Bằng chứng**: với mỗi yêu cầu, bằng chứng **kiểm được** bạn đang có (repo, bài đã pass trong repo học này, dự án,
   kinh nghiệm cụ thể có kết quả). "Đã học" hay "biết" không phải bằng chứng.
3. **Mức**: `có` (bằng chứng đủ thuyết phục người phỏng vấn), `một phần`, `chưa`.
4. **Kế hoạch**: với mỗi mục `một phần`/`chưa`, module hay bài tập hay milestone capstone cụ thể của track (hoặc track
   khác trong repo) sẽ lấp nó, sản phẩm bạn sẽ có trong tay, và hạn chót.
5. **Ba ưu tiên** trong 8 tuần tới và lý do chọn (vì sao không phải các mục khác).
6. **Câu chuyện**: một đoạn 5–8 câu bạn sẽ kể khi được hỏi "vì sao bạn hợp với vai FDE", dựa trên bằng chứng ở bảng.

Bài không có test; tự chấm theo rubric trong `SOLUTION.md`. Làm lại bài này sau trụ 1 và sau module 20 để thấy bản đồ đổi.

## Tiêu chí đạt

- 10–15 yêu cầu đã gộp, mỗi yêu cầu ghi nguồn (A, B, C).
- Mỗi mục `có` kèm bằng chứng kiểm được; không có mục `có` nào dựa trên "đã đọc" hay "đã học".
- Mỗi khoảng cách có kế hoạch trỏ tới module/bài/milestone cụ thể, sản phẩm đầu ra và hạn chót.
- Ba ưu tiên có lý do, gắn với điều cả ba tin cùng đòi hoặc với cửa đầu tiên của vòng phỏng vấn.
- Câu chuyện dựa trên bằng chứng ở bảng, không phải tính từ.

## Gợi ý

### Gợi ý 1

Gộp yêu cầu theo năng lực, không theo chữ: "Kubernetes do khách quản lý" và "triển khai trên hạ tầng của họ" có phần
chung nhưng không phải một yêu cầu.

### Gợi ý 2

Có những yêu cầu không học được trong repo (đi công tác, số năm kinh nghiệm). Ghi thật và nghĩ cách bù: chúng đổi cách
bạn kể chuyện chứ không đổi kế hoạch học.

### Gợi ý 3

Nếu bảng có quá nhiều `có`, kiểm lại bằng câu hỏi: "Người phỏng vấn mở link này ra thì thấy gì trong 2 phút?"
