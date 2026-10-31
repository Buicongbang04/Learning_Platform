---
title: Postmortem cho sự cố API 502 sau change cấu hình Nginx
level: advanced
services: []
files:
  - path: starter/POSTMORTEM.md
    note: Khung postmortem, điền mọi TODO
  - path: tests/fixtures/evidence/alerts-and-chat.txt
    note: Bằng chứng, đọc trước
  - path: tests/fixtures/evidence/chg-3107.diff
    note: Bằng chứng
  - path: tests/fixtures/evidence/nginx-error.log
    note: Bằng chứng
  - path: tests/fixtures/evidence/access-summary.txt
    note: Bằng chứng
  - path: tests/fixtures/evidence/ci-pipeline.log
    note: Bằng chứng
  - path: tests/fixtures/evidence/lb-healthcheck.txt
    note: Bằng chứng
  - path: tests/test_postmortem.py
    note: Không sửa; kiểm khung, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/advanced/01-api-outage-postmortem -q
---

## Mục tiêu

Biến một sự cố bạn đã tự tay chẩn đoán (bài Intermediate 01) thành một postmortem blameless mà người ngoài team đọc xong
hiểu chuyện gì đã xảy ra, vì sao hệ thống và quy trình để nó lọt tới production, vì sao không ai được báo, và những việc
nào làm cho lần sau máy chặn được trước khi người dùng thấy.

## Đề bài

Làm bài Intermediate 01 trước. Sự cố ở đây là bản production của nó: thứ Tư 2026-10-28, change CHG-3107 đưa API về
`/api/` cho frontend v2, rollout lúc 14:02 lên hai máy Nginx `edge-1`, `edge-2` đứng sau một load balancer cloud. Thư mục
`tests/fixtures/evidence/` có:

| Tệp | Nội dung |
| --- | --- |
| `alerts-and-chat.txt` | Kênh ops: deploy, cảnh báo, các bước xử lý, giờ São Paulo |
| `chg-3107.diff` | Diff cấu hình của change, kèm ghi chú trong PR |
| `nginx-error.log` | Trích error log của `edge-1` (đọc kỹ múi giờ của log) |
| `access-summary.txt` | Số request theo phút và theo mã, đơn hàng so với cùng giờ các tuần trước |
| `ci-pipeline.log` | Pipeline deploy cấu hình Nginx |
| `lb-healthcheck.txt` | Health check và cảnh báo của load balancer |

Dùng chúng để:

1. Xác định từng nguyên nhân kỹ thuật, trỏ về dòng bằng chứng, và giải thích vì sao lỗi thứ hai chỉ lộ ra sau khi sửa lỗi
   thứ nhất.
2. Giải thích vì sao load balancer báo xanh, vì sao `nginx -t` pass, và vì sao rollback API không giúp gì.
3. Viết `starter/POSTMORTEM.md`, giữ nguyên các heading `## 1.` tới `## 7.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Tóm tắt | Ít nhất 200 ký tự (không tính bảng) |
| 2. Tác động | Ít nhất 4 con số |
| 3. Dòng thời gian | Bảng ít nhất 10 dòng đủ 3 cột (`Thời điểm`, `Sự kiện`, `Nguồn`); cột đầu dạng `HH:MM`, tăng dần |
| 4. Nguyên nhân gốc và yếu tố góp phần | Ít nhất 500 ký tự (không tính bảng) và ít nhất 4 gạch đầu dòng |
| 5. Phát hiện và xử lý | Ít nhất 250 ký tự |
| 6. Việc cần làm | Bảng ít nhất 5 dòng đủ 4 cột (`Việc`, `Loại`, `Người phụ trách`, `Hạn`); `Loại` là một trong `phòng ngừa`, `phát hiện`, `giảm thiểu`, có ít nhất một `phòng ngừa` và một `phát hiện`; `Hạn` dạng `YYYY-MM-DD` |
| 7. Bài học | Ít nhất 2 gạch đầu dòng |

Test chỉ kiểm khung. Nội dung được chấm bằng rubric trong `solutions/advanced/01-api-outage-postmortem/SOLUTION.md`; đọc
rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/advanced/01-api-outage-postmortem -q` pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi kết luận trong phần 4 trỏ được về một dòng bằng chứng cụ thể trong `evidence/`.
- Không đổ lỗi cho cá nhân: mô tả hệ thống và quy trình đã cho phép lỗi lọt qua.
- Có ít nhất một việc cần làm biến lỗi này thành thứ pipeline chặn được, và một việc làm cho lần sau có người được báo
  trong vài phút.

## Gợi ý

### Gợi ý 1

Dòng thời gian cần cả mốc "lỗi bắt đầu", "ai đó biết", "mở sự cố", các bước chẩn đoán sai, từng lần sửa và lúc xác nhận
khôi phục. Tính time to detect và time to resolve. Log Nginx ghi giờ UTC, kênh chat ghi giờ São Paulo.

### Gợi ý 2

Hỏi "vì sao" cho từng tầng phòng thủ đã không chặn: review của PR, `nginx -t`, staging, health check của load balancer,
cảnh báo 5xx. Một tầng phòng thủ chỉ có giá trị khi nó kiểm đúng thứ hỏng: `nginx -t` kiểm cú pháp, không kiểm upstream
có trả lời không.
