---
title: Chọn loại workload, Service và storage cho từng thành phần của Olist Shop
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung tài liệu thiết kế
  - path: tests/test_design.py
    note: Kiểm cấu trúc và vài lựa chọn có đáp án rõ, không sửa
  - path: tests/fixtures/DESIGN.good.md
    note: Ví dụ đạt (hệ thống khác)
run:
  - uv run pytest tracks/devops/modules/10-kubernetes-core/exercises/advanced/01-workload-types-design -q -rs
---

## Mục tiêu

Ra quyết định kiến trúc có lý lẽ cho một hệ thống thật trên Kubernetes: mỗi thành phần chạy bằng workload nào (hay không chạy trong
cluster), lộ ra bằng Service gì, giữ dữ liệu ở đâu, probe ra sao, rollout thế nào, và cái giá của từng lựa chọn.

## Đề bài

Olist Shop chuẩn bị lên production trên một cluster managed ba AZ (4 tới 20 node). Đội platform bốn người. Các thành phần:

- `api`: FastAPI, 150 request/giây lúc thường, 1.200 lúc đỉnh 11.11.
- `worker`: đọc hàng đợi Redis, tính doanh thu; không ai gọi vào.
- `postgres`: dữ liệu đơn hàng, RPO 5 phút, RTO 30 phút.
- `redis`: hàng đợi job và cache; mất thì API enqueue lại được.
- `fluent-bit`: agent thu log từ mọi container trên mỗi node.
- `report`: báo cáo doanh thu lúc 02:00 giờ Việt Nam mỗi ngày.
- `migration`: đổi schema đi kèm mỗi release, khoảng 10 lần mỗi tuần.
- `thumbnail`: mỗi đợt nhập hàng tạo thumbnail cho 10.000 ảnh, chia 20 phần, xong trong một giờ.
- `payment`: cổng thanh toán HTTPS của đối tác ở `payments.partner.example`.

Điền `starter/DESIGN.md` (giữ đúng 6 tiêu đề `## 1.` tới `## 6.`). Bảng ở phần 2 có đúng 6 cột theo thứ tự: Thành phần, Workload,
Service, Storage, Probe, Lý do; ô đầu mỗi dòng chứa tên thành phần như trên.

| Phần | Test kiểm |
| --- | --- |
| Toàn tài liệu | Không còn `TODO` |
| 1. Bối cảnh | Ít nhất 300 ký tự văn xuôi |
| 2. Bảng quyết định | Một dòng cho mỗi thành phần trong 9 thành phần; cột Workload là `Deployment`, `StatefulSet`, `DaemonSet`, `Job`, `CronJob`, `Pod tĩnh` hay `Không chạy trong cluster`; cột Service là `ClusterIP`, `Headless`, `NodePort`, `LoadBalancer`, `ExternalName` hay `Không`; cột Storage không dùng hostPath; lý do ít nhất 25 ký tự |
| 2. Lựa chọn có đáp án rõ | `fluent-bit` là DaemonSet; `report` là CronJob; `migration` và `thumbnail` là Job; `postgres` là StatefulSet hay Không chạy trong cluster; Service của `payment` là ExternalName |
| 3. Sơ đồ | Khối mermaid; phần này nhắc Ingress hay Gateway, và Service |
| 4. Rollout | Ít nhất 4 gạch đầu dòng; nhắc maxUnavailable hay maxSurge, partition hay OnDelete hay podManagementPolicy, PodDisruptionBudget (PDB) |
| 5. Storage | Ít nhất 3 gạch đầu dòng; nhắc StorageClass, ReadWriteOnce (RWO), Retain hay reclaim, backup hay snapshot hay pg_dump |
| 6. Rủi ro | Ít nhất 4 gạch đầu dòng |

Test chỉ kiểm cấu trúc, từ khoá và sáu lựa chọn ở trên; chất lượng lập luận chấm bằng rubric trong `SOLUTION.md` (tự chấm hoặc nhờ
người review).

**Cách test chấm.** Đọc `starter/DESIGN.md` và chạy cùng bộ kiểm trên ba fixture (khung, bản yếu, bản đạt của một hệ thống khác) để
chứng minh bộ kiểm bắt được lỗi. Không cần cluster.

## Tiêu chí đạt

- Test pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10: mỗi lựa chọn có lý do gắn với số liệu của đề, nêu rõ cái giá.
- Bảo vệ được quyết định trước hai câu hỏi: "Vậy sao không chạy Postgres bằng StatefulSet cho rẻ?" (hay ngược lại "sao không dùng
  RDS?"), và "Redis restart lúc 11.11 thì mất gì?".

## Gợi ý

### Gợi ý 1

Ba câu hỏi tách workload: thành phần có chạy mãi không (Deployment, StatefulSet, DaemonSet) hay chạy xong là hết (Job, CronJob);
replica có cần danh tính và volume riêng không; có phải chạy trên **mọi** node không. Thứ không thuộc cluster vẫn có thể có Service
(ExternalName, hay Service không selector cộng EndpointSlice tay).

### Gợi ý 2

Đọc `tests/fixtures/DESIGN.good.md` để thấy độ chi tiết mong đợi (hệ thống khác, đừng chép). Phần rollout của StatefulSet: một
replica chết khi đang nâng cấp và `partition` cho phép làm gì.
