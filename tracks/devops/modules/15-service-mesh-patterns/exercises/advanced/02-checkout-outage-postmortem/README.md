---
title: Postmortem và review kiến trúc theo pattern - checkout lỗi hàng loạt ngày Black Friday
level: advanced
services: []
files:
  - path: starter/POSTMORTEM.md
    note: Khung postmortem, 7 phần
  - path: tests/fixtures/evidence/metrics.csv
    note: Số liệu theo phút, 14:00 tới 14:40
  - path: tests/fixtures/evidence/events.log
    note: Deploy, alert, chat của on-call
  - path: tests/fixtures/evidence/configs.yaml
    note: Cấu hình client và tài nguyên lúc sự cố
  - path: tests/test_postmortem.py
    note: Kiểm khung tài liệu và số liệu; không sửa
  - path: tests/fixtures/POSTMORTEM.good.md
    note: Ví dụ đạt (sự cố khác, dữ liệu trong tests/fixtures/sample/)
run:
  - uv run pytest tracks/devops/modules/15-service-mesh-patterns/exercises/advanced/02-checkout-outage-postmortem -q
---

## Mục tiêu

Viết một postmortem blameless từ bằng chứng thô: dựng timeline, đo tác động bằng số, tìm nguyên nhân gốc chứ không dừng ở thứ kích
hoạt, giải thích vì sao các hành động khắc phục đầu tiên không hiệu quả, rồi review kiến trúc theo bốn nhóm cloud design pattern để ra
action item đo được.

## Đề bài

Ngày 2026-11-27 (Black Friday), từ khoảng 14:10 giờ São Paulo, phần lớn lượt thanh toán của Olist Shop thất bại trong khoảng nửa giờ. Luồng
thanh toán: khách → `storefront` → `api` → `payments` → (`fraud-score`, Postgres `ledger`). On-call đã scale, đã rollback, và sự cố
chỉ hết sau một thay đổi cấu hình. Bạn có ba tệp bằng chứng trong `tests/fixtures/evidence/`:

- `metrics.csv`: mỗi phút một dòng, cột `minute`, `checkout_rps` (request khách gửi vào storefront mỗi giây), `payments_rps` (request
  payments nhận mỗi giây), `payments_error_pct`, `payments_p99_ms`, `orders_failed` (số đơn thất bại trong phút đó).
- `events.log`: deploy, alert, hành động và tin nhắn của on-call.
- `configs.yaml`: timeout, retry, tài nguyên của từng tầng lúc sự cố.

Viết `starter/POSTMORTEM.md`, giữ bảy tiêu đề `## 1.` tới `## 7.`:

| Phần | Nội dung | Test kiểm |
| --- | --- | --- |
| 1. Tóm tắt | Chuyện gì xảy ra, bao lâu, vì sao, hết thế nào | ≥3 gạch đầu dòng; có thời lượng sự cố bằng số phút: số phút trong `metrics.csv` có `payments_error_pct` từ 5 trở lên |
| 2. Tác động | Đo bằng số | Có tổng số đơn thất bại (cộng cột `orders_failed`); có `checkout_rps` và `payments_rps` của phút payments nhận nhiều request nhất |
| 3. Timeline | Bảng cột `Thời điểm`, `Sự kiện` | ≥6 mốc giờ `HH:MM` theo thứ tự; có mốc phút đầu tiên lỗi payments từ 5% trở lên |
| 4. Nguyên nhân | `### Vì sao` (chuỗi vì sao, đánh số) và `### Yếu tố góp phần` | ≥3 bước đánh số; ≥2 gạch đầu dòng |
| 5. Review theo pattern | Bảng cột `Pattern`, `Nhóm`, `Hiện trạng`, `Đề xuất` | ≥6 dòng; mỗi pattern thuộc danh sách dưới đây và đúng nhóm; phủ đủ bốn nhóm |
| 6. Action items | Bảng cột `Việc`, `Loại`, `Người phụ trách`, `Hạn` | ≥5 việc; `Loại` là `Phòng ngừa`, `Phát hiện` hay `Giảm thiểu`, đủ cả ba; hạn `YYYY-MM-DD` sau ngày sự cố; có người phụ trách |
| 7. Bài học | Điều tổ chức học được | ≥2 gạch đầu dòng |

Số viết liền hay có dấu cách, chấm, phẩy giữa các nhóm ba chữ số đều được (`12345`, `12 345`, `12.345`).

Pattern và nhóm hợp lệ (theo mục 6, 7 của README module):

| Nhóm | Pattern |
| --- | --- |
| Availability | Retry, Circuit Breaker, Bulkhead, Throttling, Rate Limiting, Queue-Based Load Leveling, Deployment Stamps, Health Endpoint Monitoring |
| Data Management | Cache-Aside, CQRS, Event Sourcing, Materialized View, Sharding, Saga, Compensating Transaction, Transactional Outbox |
| Design & Implementation | Sidecar, Ambassador, Anti-Corruption Layer, Strangler Fig, Backends for Frontends, Gateway Routing, Gateway Offloading |
| Management & Monitoring | Health Endpoint Monitoring, External Configuration Store, Gateway Routing, Gateway Offloading |

Postmortem là blameless: viết về hệ thống và quyết định, không về lỗi của cá nhân. Test kiểm khung và các con số lấy từ bằng chứng;
rubric chấm lập luận. Test còn chạy bộ kiểm trên ba fixture (khung, bản yếu, bản đạt cho một sự cố khác) để chứng minh bắt được lỗi.

## Tiêu chí đạt

- Test pass.
- Rubric trong `solutions/advanced/02-checkout-outage-postmortem/SOLUTION.md` đạt từ 7/10.
- Trả lời được: "Vì sao scale lên 8 pod không giúp?", "Vì sao rollback lúc 14:24 không đủ?", "Nếu chỉ được làm một action item trước
  Black Friday năm sau, bạn chọn cái nào và đo nó thế nào?".

## Gợi ý

### Gợi ý 1

Đặt cạnh nhau các cột của `metrics.csv` theo từng phút, nhất là hai cột lưu lượng, và đối chiếu với `configs.yaml`: mỗi con số trong
cấu hình có thể giải thích một hình dạng trong số liệu. Một bảng tính hay vài dòng pandas là đủ.

### Gợi ý 2

Thứ kích hoạt sự cố và thứ giữ sự cố kéo dài có thể là hai chuyện khác nhau. Với mỗi hành động của on-call, hỏi: nó đổi được đại
lượng nào trong số liệu, và vì sao đại lượng đó không phải nút cổ chai.
