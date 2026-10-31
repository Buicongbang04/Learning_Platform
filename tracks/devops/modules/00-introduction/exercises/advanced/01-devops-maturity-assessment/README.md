---
title: Đánh giá độ trưởng thành DevOps của team Checkout
level: advanced
services: []
files:
  - path: starter/ASSESSMENT.md
    note: Khung báo cáo, điền mọi TODO
  - path: tests/test_assessment.py
    note: Không sửa; chỉ kiểm khung và mức DORA, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/00-introduction/exercises/advanced/01-devops-maturity-assessment -q
---

## Mục tiêu

Làm việc một DevOps/SRE senior hay được giao trong tuần đầu ở công ty mới: đọc hiện trạng một team, đo bằng DORA,
chấm theo CALMS có bằng chứng, tìm nguyên nhân gốc thay vì triệu chứng, và đưa ra kế hoạch 90 ngày nhỏ, đo được, có
nói rõ điều sẽ **không** làm.

## Đề bài

Bạn vừa vào làm ở một sàn thương mại điện tử (120 kỹ sư). CTO nhờ bạn đánh giá **team Checkout** (9 dev, 2 QA) và
đề xuất cải thiện. Bạn có hai tuần phỏng vấn và đọc dữ liệu. Ghi chép của bạn:

**Số liệu 12 tháng qua (từ Jira, GitLab và kênh #incident)**

- Release train hai tuần một lần, thứ Năm. 24 release đúng lịch, 2 release ngoài lịch (hotfix khẩn). Không deploy
  ngoài release train trừ hotfix.
- Median từ commit tới production: 19 ngày. Nhánh `release/*` cắt sớm 5 ngày để QA test tay.
- 26 lần deploy production thì 9 lần phải hotfix hoặc rollback trong vòng 48 giờ.
- Release lỗi được sửa trong release kế tiếp hoặc hotfix sau khi CAB duyệt. Median từ lúc release lỗi tới lúc khôi
  phục: 9 ngày. Rollback cần ops chạy tay theo runbook trên Confluence, mất khoảng 2 giờ.
- Không có SLO. Availability đo bằng ping từ bên ngoài mỗi phút: 99,95% năm qua, nhưng 3 lần lỗi thanh toán kéo
  dài (mỗi lần trả lỗi cho 2–8% giao dịch trong vài giờ) không hiện trên ping.

**Phỏng vấn và quan sát**

- Ops là team riêng (5 người) dưới một giám đốc khác. Dev mở ticket xin môi trường, SLA 5 ngày làm việc.
- CAB họp thứ Ba, duyệt mọi thay đổi production, kể cả đổi một biến môi trường.
- Postmortem có, nhưng mục "nguyên nhân" thường ghi tên người; action item ít khi có người nhận.
- Test tự động: unit test chạy trong CI (độ phủ 45%), không có integration test, regression do QA làm tay 3 ngày.
- Môi trường staging cấu hình tay, khác production (khác phiên bản Postgres, không có Redis cluster).
- Monitoring: Zabbix báo CPU, RAM, đĩa; không có metric ứng dụng; dev không có quyền xem log production.
- Một dev senior viết script deploy riêng, chỉ anh ấy hiểu; anh ấy sắp nghỉ.
- Team muốn chuyển sang Kubernetes "để deploy nhanh hơn". Ban giám đốc muốn KPI "deploy hằng ngày" trong quý tới.

Điền `starter/ASSESSMENT.md`:

1. **Số liệu DORA**: giá trị của bốn metric từ ghi chép, mức theo bảng DORA 2024 (`elite`, `high`, `medium`, `low`),
   và ghi chú đo lường (số liệu nào bạn tin, số nào cần đo lại, đo bằng gì).
2. **CALMS**: điểm 1–5 cho từng trụ cột, mỗi điểm kèm bằng chứng cụ thể từ ghi chép.
3. **Nguyên nhân gốc**: ít nhất 3, viết dạng nguyên nhân chứ không phải triệu chứng.
4. **Kế hoạch 90 ngày**: ít nhất 3 việc, mỗi việc nêu metric DORA (hoặc reliability) kỳ vọng cải thiện, cách đo,
   rủi ro hoặc đánh đổi.
5. **Không làm trong 90 ngày tới**: ít nhất 2 việc kèm lý do (gợi ý: hai đề xuất cuối của ghi chép).

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/00-introduction/exercises/advanced/01-devops-maturity-assessment -q` pass:
  không còn TODO, mức DORA đúng với số liệu, đủ các phần. Test chỉ kiểm khung; chất lượng chấm theo rubric trong
  `solutions/advanced/01-devops-maturity-assessment/SOLUTION.md`.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Kế hoạch đọc được bởi CTO trong 5 phút: mỗi việc có người chịu trách nhiệm dự kiến và tín hiệu thành công.

## Gợi ý

### Gợi ý 1

Đổi số liệu về đơn vị của bảng DORA trước khi xếp mức: 26 deploy/năm là bao nhiêu lần mỗi tuần? 9/26 là bao nhiêu
phần trăm, và nó gần cụm nào nhất? Lưu ý bảng 2024 là kết quả phân cụm, nên change failure rate của cụm high (20%)
cao hơn cụm medium (10%); với một metric đứng riêng, chọn cụm có giá trị gần nhất và ghi rõ điều đó.

### Gợi ý 2

Hỏi "vì sao" ít nhất ba lần cho mỗi triệu chứng. Lead time 19 ngày vì release train; release train tồn tại vì
regression test tay mất 3 ngày và CAB họp hằng tuần; CAB tồn tại vì change failure rate cao. Một kế hoạch tốt cắt
vòng lặp này ở chỗ rẻ nhất, thường là tự động hoá test và rollback, rồi mới nới CAB.
