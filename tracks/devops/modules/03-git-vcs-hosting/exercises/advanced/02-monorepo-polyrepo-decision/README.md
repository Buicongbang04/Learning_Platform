---
title: Monorepo hay polyrepo cho Olist Shop - viết ADR có ràng buộc quyền truy cập
level: advanced
services: []
files:
  - path: starter/DECISION.md
    note: Khung ADR, điền mọi TODO
  - path: tests/test_decision.py
    note: Không sửa; kiểm khung, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/advanced/02-monorepo-polyrepo-decision -q
---

## Mục tiêu

Ra quyết định cấu trúc repo từ nỗi đau đo được và ràng buộc thật (quyền truy cập, CI, kỹ năng team), không từ việc
"Google dùng monorepo". Biết cái giá của từng hướng, và lập kế hoạch chuyển đổi giữ được lịch sử, không dừng việc của
team.

## Đề bài

Olist Shop có 9 repo cho 25 kỹ sư: `api` (FastAPI), `worker`, `web` (Next.js), `mobile-bff`, thư viện `olist-common`
(phát hành lên PyPI nội bộ, các service pin phiên bản), `dbt`, `infra-tofu`, `helm-charts`, `ci-templates`. Ghi nhận
trong quý:

- Thêm một trường vào đơn hàng cần PR ở `olist-common`, `api`, `worker`, `helm-charts`, merge đúng thứ tự, trung bình 3
  ngày. Hai lần merge sai thứ tự làm production lỗi.
- Production chạy 3 phiên bản `olist-common` khác nhau; một bản vá bảo mật mất 2 tuần mới tới mọi service.
- 9 bản sao workflow CI lệch nhau; 2 repo chưa có quét secret.
- Người mới cần clone 9 repo và đọc 9 README để chạy được hệ thống trên máy.

Ràng buộc:

- Contractor bên ngoài làm `web` **không được đọc** code thanh toán trong `api` (yêu cầu PCI DSS và hợp đồng).
- Team data muốn giữ quyền và nhịp phát hành riêng cho `dbt`.
- Ngân sách GitHub Actions không được tăng quá 20%.
- Không ai trong team từng vận hành Bazel hay Pants.
- Lịch sử repo `web` có khoảng 2 GB ảnh thiết kế.

Viết `starter/DECISION.md` dạng ADR, giữ nguyên các heading `## 1.` tới `## 7.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh | Ít nhất 250 ký tự |
| 2. Phương án | Bảng ít nhất 3 dòng đủ 6 cột theo khung; cột đầu của một dòng chứa `mono` và của một dòng chứa `poly` hoặc `multi` (không phân biệt hoa thường); cột cuối là số nguyên 1–5 |
| 3. Quyết định | Dòng `Chọn: <phương án>`, phần sau `Chọn:` chứa nguyên văn cột đầu của một dòng trong bảng; cả phần ít nhất 300 ký tự |
| 4. Tác động lên CI/CD, quyền truy cập và CODEOWNERS | Ít nhất 3 gạch đầu dòng |
| 5. Kế hoạch chuyển đổi | Ít nhất 4 bước đánh số |
| 6. Rủi ro và đánh đổi | Ít nhất 3 gạch đầu dòng |
| 7. Khi nào xem lại quyết định | Ít nhất 2 gạch đầu dòng |

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/advanced/02-monorepo-polyrepo-decision -q` pass.
  Test chỉ kiểm khung và độ dài; chất lượng chấm theo rubric trong
  `solutions/advanced/02-monorepo-polyrepo-decision/SOLUTION.md`.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi ô của bảng phương án là nhận định kiểm chứng được cho **tình huống này** (ví dụ "contractor thấy code thanh
  toán"), không phải nhận xét chung kiểu "dễ quản lý".

## Gợi ý

### Gợi ý 1

Viết ra ba nỗi đau lớn nhất và hỏi: phương án nào xoá nỗi đau đó **theo cấu trúc**, phương án nào chỉ giảm bằng công cụ
(Renovate tự nâng phiên bản, reusable workflow chung)? Rồi kiểm từng phương án với ràng buộc cứng: GitHub và GitLab
cấp quyền đọc theo repo, không theo thư mục.

### Gợi ý 2

Không bắt buộc chọn một trong hai cực. Kế hoạch chuyển đổi nên giữ lịch sử (`git filter-repo --to-subdirectory-filter`
rồi merge với `--allow-unrelated-histories`, hoặc `git subtree add`), đi từng repo một, và để repo cũ ở chế độ chỉ đọc
có README trỏ sang chỗ mới. Đừng mang 2 GB ảnh vào repo mới: nếu gộp `web`, chuyển ảnh sang Git LFS hoặc kho tài sản
riêng trước.
