---
title: Thiết kế pipeline nhiều môi trường có rollback cho Olist Shop
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung thiết kế, điền mọi TODO
  - path: tests/test_design.py
    note: Không sửa; kiểm khung và vài quyết định đo được, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/07-cicd-artifacts/exercises/advanced/01-multi-env-pipeline-design -q
---

## Mục tiêu

Thiết kế đường đi của một thay đổi từ commit tới production qua nhiều môi trường, sao cho: thứ lên production đúng là thứ đã được
kiểm, mỗi bước có gate đo được, rollback là thao tác có sẵn và có thời hạn, và migration cơ sở dữ liệu không biến rollback thành
không thể.

## Đề bài

Olist Shop gồm `api`, `worker`, Postgres, Redis và một job `seed`. Hiện trạng:

- Deploy bằng tay mỗi thứ Năm: một kỹ sư build image trên laptop, đẩy tag `latest`, SSH vào máy chạy `docker compose pull && up`.
- 6 tháng qua: 26 lần deploy, 5 lần phải sửa gấp (một lần mất 3 giờ vì không biết bản trước là image nào), một lần migration đổi
  tên cột làm `api` cũ lỗi 20 phút giữa lúc rollout.
- Từ quý sau, Olist Shop chạy trên Kubernetes (module 10, 11) với ba môi trường; registry là GHCR; CI là GitHub Actions.
- Team: 4 kỹ sư backend, 1 người vận hành (bạn). Kinh doanh muốn release nhiều lần mỗi ngày trong mùa Black Friday, nhưng không
  chấp nhận lỗi thanh toán quá 5 phút.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 8.`, không còn chữ `TODO`. Bài này là thiết kế; capstone m04 mới hiện
thực một phần của nó (test, build, push, deploy staging).

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và mục tiêu | Ít nhất 300 ký tự (không tính bảng và khối code); nói tới lead time, change failure rate và MTTR (hay tương đương tiếng Việt: thời gian từ commit, tỉ lệ thay đổi lỗi, thời gian khôi phục) |
| 2. Môi trường và promotion | Bảng ít nhất 3 dòng đủ 5 cột (`Môi trường`, `Trigger`, `Phê duyệt`, `Artifact`, `Dữ liệu`); có dòng chứa `staging` và dòng chứa `production`; cột Artifact của hai dòng đó có chữ `digest` và không có `latest`; cột Phê duyệt của production không được là `không`, `-`, `tự động` hay để trống |
| 3. Sơ đồ pipeline | Một khối mermaid có các chữ `staging`, `production`, `rollback` |
| 4. Chiến lược deploy theo service | Bảng ít nhất 3 dòng đủ 4 cột (`Service`, `Chiến lược`, `Lý do`, `Tín hiệu rollback`); mỗi chiến lược là một trong rolling, blue/green (hay blue-green), canary, recreate, feature flag, shadow; ít nhất 2 chiến lược khác nhau |
| 5. Rollback và migration cơ sở dữ liệu | Ít nhất 5 gạch đầu dòng; có `digest`, `expand`, `contract`, `feature flag` (hay `flag`); có một mục tiêu thời gian dạng `<số> phút` |
| 6. Bí mật và quyền | Ít nhất 4 gạch đầu dòng; có `OIDC`, `environment`, `permissions` (hay `quyền tối thiểu`) |
| 7. Gate tự động và quan sát | Bảng ít nhất 4 dòng đủ 3 cột (`Gate`, `Ngưỡng`, `Hành động`); ít nhất 3 ngưỡng có số; có một gate theo tỉ lệ lỗi (lỗi, error, 5xx) và một gate theo độ trễ (p95, p99, latency, độ trễ) |
| 8. Rủi ro và lộ trình triển khai | Ít nhất 4 gạch đầu dòng |

Test chỉ kiểm khung và các quyết định trên; hai test khác đưa khung trống và một thiết kế yếu (production deploy `latest` không
phê duyệt, sơ đồ không có rollback, mọi service rolling, rollback bằng build lại, gate không có số, `write-all`, không OIDC) vào
cùng phép kiểm và đòi bị bắt. Nội dung chấm bằng rubric trong `solutions/advanced/01-multi-env-pipeline-design/SOLUTION.md`; đọc
rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/07-cicd-artifacts/exercises/advanced/01-multi-env-pipeline-design -q` pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Trả lời được: lúc 2 giờ sáng `api` bản mới làm lỗi thanh toán, ai làm gì trong 5 phút đầu, bằng lệnh hay nút nào, và vì sao
  thao tác đó không phụ thuộc migration vừa chạy.
- Mỗi gate có chỗ thực thi cụ thể (bước CI, environment protection rule, phân tích của công cụ rollout) và người sở hữu.

## Gợi ý

### Gợi ý 1

Build một lần, promote nhiều lần: image được build và gắn digest ở bước CI, mọi môi trường sau chỉ nhận digest đó cùng cấu hình
riêng của môi trường. Môi trường production trên GitHub là một `environment` có required reviewers, wait timer và giới hạn nhánh;
secret của production chỉ job gắn environment đó đọc được, và token OIDC của job đó mới được cloud tin.

### Gợi ý 2

Rollback nhanh chỉ có được khi bản trước vẫn chạy được trên schema hiện tại. Viết migration theo expand/contract và tách migration
khỏi deploy code; tính năng rủi ro đặt sau feature flag để "rollback" là tắt flag. Đặt thời gian rollback mục tiêu bằng con số và
đo nó trong game day.
