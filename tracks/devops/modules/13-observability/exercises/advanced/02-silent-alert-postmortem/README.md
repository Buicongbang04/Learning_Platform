---
title: Postmortem - 56 phút khách không đặt được hàng mà không ai bị page
level: advanced
services: []
files:
  - path: starter/POSTMORTEM.md
    note: Khung postmortem, 8 phần
  - path: evidence/alertmanager.yml
    note: Cấu hình Alertmanager lúc xảy ra sự cố
  - path: evidence/alerts-2026-10-21T21-45.json
    note: Kết quả /api/v2/alerts lúc 21:45 (giờ UTC trong tệp)
  - path: tests/test_postmortem.py
    note: Kiểm cấu trúc, thứ tự, số liệu, từ khoá; không sửa
  - path: tests/fixtures/POSTMORTEM.good.md
    note: Ví dụ đạt (sự cố khác)
run:
  - uv run pytest tracks/devops/modules/13-observability/exercises/advanced/02-silent-alert-postmortem -q -rs
---

## Mục tiêu

Viết postmortem không đổ lỗi cho một sự cố mà hệ thống alert "im lặng": tự tìm ra từ bằng chứng vì sao một alert đúng, đã bắn, lại
không tới người trực; tính đúng thời gian ảnh hưởng và thời gian phát hiện; và đưa ra action item chặn cả lớp lỗi này chứ không chỉ lần
này.

## Đề bài

Dữ kiện người trực gom được ngày 2026-10-21 (giờ Việt Nam), chưa theo thứ tự:

- 21:52 Rollback API về v2.13.
- 18:02 Alert `MaintenanceMode` của team Search bắt đầu bắn (metric `olist_maintenance_mode{service="olist-search"} == 1`): reindex có kế
  hoạch, báo trước trong kênh chung, dự kiến tới 02:00.
- 21:02 API bắt đầu trả 503 cho khoảng 35% request đặt hàng và tra đơn. Log: `QueuePool limit of size 5 overflow 0 reached`.
- 21:41 Người trực mở Grafana: tỉ lệ 5xx 34,8%. Trong UI Alertmanager, `OlistApiHighErrorRate` hiện trạng thái `suppressed`.
- 20:47 Deploy API v2.14 (đổi cấu hình pool kết nối Postgres). Canary 5 phút không thấy lỗi vì traffic buổi tối còn thấp.
- 21:09 Prometheus: `OlistApiHighErrorRate` chuyển `firing`, gửi tới Alertmanager. Không có page nào tới pager.
- 21:58 Tỉ lệ 5xx dưới 1%.
- 21:38 Team chăm sóc khách hàng báo trong #olist-ops: 32 ticket "không đặt được hàng" trong nửa giờ.
- 21:14 `OlistCheckoutLatencyHigh` chuyển `firing`. Không có page nào.
- 22:10 Người trực và một kỹ sư platform đọc `evidence/alertmanager.yml`.
- 22:40 Sau khi sửa cấu hình Alertmanager, gửi một alert thử bằng `amtool alert add`: pager rung.
- 23:00 Đóng sự cố. `MaintenanceMode` vẫn bắn tới 02:00 như kế hoạch.

Thêm:

- Heartbeat của Watchdog tới dịch vụ bên ngoài đều đặn suốt buổi tối; dịch vụ đó không báo gì.
- Luật thứ hai trong `inhibit_rules` được team Search thêm 3 tuần trước trong PR "im alert khi bảo trì". PR qua `amtool check-config` trong
  CI và được một người team Search duyệt. Không có test nào chạy Alertmanager thật.
- Ngày 2026-10-08, trong một đợt bảo trì khác của Search (14:00 tới 18:00), ticket `OlistPostgresDiskFillingUp` của Olist Shop không được
  tạo; đĩa được phát hiện ở mức 91% hai ngày sau qua dashboard.
- Trung bình khoảng 95 lượt đặt hàng mỗi phút vào giờ đó; số đơn thất bại ước tính 1.900, khoảng 60% khách thử lại thành công sau 22:00.
- `evidence/alerts-2026-10-21T21-45.json` là kết quả `GET /api/v2/alerts` lúc 21:45 (thời gian trong tệp là UTC).

Điền `starter/POSTMORTEM.md`, giữ đúng tám tiêu đề `## 1.` tới `## 8.`. Test chỉ kiểm phần chấm được bằng máy; rubric trong `SOLUTION.md`
chấm nội dung.

**Cách test chấm.**

| Phần | Test kiểm |
| --- | --- |
| Khung | Đủ `## 1.` tới `## 8.`, không còn `TODO` |
| 1. Tóm tắt | Ít nhất 250 ký tự văn xuôi |
| 2. Tác động | Thời gian ảnh hưởng đúng theo dữ kiện (số phút), nhắc đơn hàng và khách |
| 3. Timeline | Ít nhất 8 dòng bảng có cột đầu là giờ `HH:MM`, theo thứ tự thời gian |
| 4. Nguyên nhân | Ít nhất 3 gạch đầu dòng; chỉ ra đúng cơ chế cấu hình và phần thiếu trong đó (kiểm bằng từ khoá, không công bố: bằng chứng đủ để tự tìm) |
| 5. Phát hiện và xử lý | Thời gian từ lúc bắt đầu lỗi tới lúc con người biết (số phút); nhắc rollback |
| 6. Chạy tốt, chưa tốt | Ít nhất 3 gạch đầu dòng; nhắc Watchdog |
| 7. Bài học | Ít nhất 3 gạch đầu dòng |
| 8. Action items | Bảng ít nhất 5 dòng, mỗi dòng có người phụ trách (cột 2) và hạn `YYYY-MM-DD`; có action item phòng ngừa đúng cơ chế ở phần 4 và action item kiểm cấu hình alert trên hệ thống thật (từ khoá, không công bố) |
| Bộ kiểm | Chạy phần kiểm chung trên ba fixture (khung, bản yếu, bản đạt của sự cố khác) để chứng minh bắt được lỗi |

## Tiêu chí đạt

- Test pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10.
- Trả lời được: "Vì sao Watchdog không cứu được?", "Vì sao `amtool check-config` qua mà cấu hình vẫn sai?", "Sự cố ngày 2026-10-08 liên
  quan gì?", "Lần sau ai sẽ biết trước, sau bao nhiêu phút?".

## Gợi ý

### Gợi ý 1

Đi theo đường đi của một alert: Prometheus đánh giá rule → gửi Alertmanager → route → (silence? inhibit?) → receiver → pager. Bằng chứng
cho thấy alert đã đi tới bước nào? Trường `inhibitedBy` trỏ tới `fingerprint` của alert nào?

### Gợi ý 2

So luật thứ hai trong `inhibit_rules` với luật thứ nhất ngay trên nó. Rồi hỏi: luật đó được viết cho ai, và nó thực sự áp dụng cho ai? Mỗi
nguyên nhân hệ thống (review, CI, cách mô hình hoá bảo trì, cách giám sát chính hệ thống alert) nên có ít nhất một action item.
