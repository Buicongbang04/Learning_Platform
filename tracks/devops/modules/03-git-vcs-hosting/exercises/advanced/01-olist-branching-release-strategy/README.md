---
title: Thiết kế chiến lược nhánh, phát hành và CODEOWNERS cho Olist Shop
level: advanced
services: []
files:
  - path: starter/STRATEGY.md
    note: Khung tài liệu, điền mọi TODO
  - path: starter/CODEOWNERS
    note: Viết các dòng theo bảng owner trong đề
  - path: tests/test_strategy.py
    note: Không sửa; kiểm khung và CODEOWNERS, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/advanced/01-olist-branching-release-strategy -q
---

## Mục tiêu

Thiết kế cách một team đi từ "deploy mỗi thứ Năm" tới "deploy mỗi ngày" mà vẫn qua được audit: mô hình nhánh, đường
promote qua dev, staging, prod, luồng hotfix, ruleset và CODEOWNERS, và cách đo bằng DORA để biết thay đổi có hiệu quả.

## Đề bài

Olist Shop là một monorepo: `services/api` (FastAPI, có `services/api/app/payments/` và `services/api/migrations/`),
`services/worker`, `analytics/dbt`, `infra/tofu`, `deploy/helm`, `.github/workflows`. Năm team trên GitHub:
`@olist-shop/backend` (6 người), `@olist-shop/payments` (3), `@olist-shop/platform` (2), `@olist-shop/security` (1,
dùng chung với team khác), `@olist-shop/data` (2).

Hiện trạng: `develop` và `release/*` kiểu GitFlow; deploy production thứ Năm hằng tuần sau 2 ngày QA trên nhánh
release; lead time khoảng 9 ngày; change failure rate 20%; hai lần mỗi tháng hotfix bằng cách sửa thẳng trên server.
Ràng buộc bắt buộc:

- Code thanh toán thuộc phạm vi PCI DSS: mọi thay đổi trong đó cần review của payments **và** security.
- Deploy production cần người duyệt khác người viết thay đổi (separation of duties).
- Migration phải tương thích ngược: bản cũ và bản mới của API chạy song song khi rolling deploy.
- App mobile gọi API; endpoint cũ phải còn chạy ít nhất 2 tuần sau khi có bản mới.
- Mục tiêu của ban lãnh đạo: deploy hằng ngày trong hai quý, change failure rate không tăng.

**1. `starter/STRATEGY.md`**: điền khung, giữ nguyên các heading `## 1.` tới `## 7.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và ràng buộc | Ít nhất 250 ký tự |
| 2. Mô hình nhánh | Một khối ` ```mermaid ` mở đầu bằng `gitGraph`; ít nhất 200 ký tự giải thích ngoài sơ đồ |
| 3. Đường đi tới dev, staging, prod | Bảng ít nhất 3 dòng, đủ 5 cột của khung, cột đầu các dòng chứa `dev`, `staging`, `prod` |
| 4. Hotfix | Ít nhất 4 bước đánh số (`1.`, `2.`...) |
| 5. Bảo vệ nhánh và rulesets | Bảng ít nhất 4 dòng, đủ 3 cột |
| 6. Đo bằng DORA | Ít nhất 3 gạch đầu dòng; cả phần nhắc ít nhất 3 trong 4 chỉ số: `deployment frequency` (hoặc `tần suất deploy`), `lead time`, `change failure`, `recovery time` (hoặc `MTTR`, `thời gian khôi phục`), không phân biệt hoa thường |
| 7. Đánh đổi và khi nào xem lại | Ít nhất 3 gạch đầu dòng |

**2. `starter/CODEOWNERS`** (trong repo thật đặt ở `.github/CODEOWNERS`). Mỗi dòng không phải comment là
`<pattern> <owner>...`; owner **chỉ** là một trong năm team trên, viết `@olist-shop/<team>`. Như GitHub: **dòng khớp
sau cùng thắng**, owner của các dòng trước bị bỏ hoàn toàn. Test tính owner của từng đường dẫn dưới đây và đòi đúng
**tập** owner (không thừa, không thiếu):

| Đường dẫn | Owner |
| --- | --- |
| `README.md`, `services/api/app/main.py`, `services/worker/tasks.py` | backend |
| `services/api/app/payments/pix.py` | payments, security |
| `services/api/migrations/0042_add_pix.sql` | backend, data |
| `services/api/Dockerfile` (Dockerfile ở mọi thư mục) | backend, platform |
| `analytics/dbt/models/orders.sql` | data |
| `infra/tofu/main.tf`, `tools/legacy/network.tf` (tệp `.tf` ở mọi nơi), `deploy/helm/values-prod.yaml` | platform |
| `.github/workflows/ci.yml`, `.github/CODEOWNERS` | platform, security |

Test dùng ngữ nghĩa pattern của GitHub cho các dạng sau (không dùng `!`, `[ ]`, `\`: GitHub không hỗ trợ):

| Pattern | Khớp |
| --- | --- |
| `*` | Mọi tệp |
| `*.tf`, `Dockerfile` (không có `/`) | Tên tệp đó ở mọi thư mục |
| `/infra/` | Mọi thứ dưới `infra/` ở gốc repo, mọi độ sâu |
| `docs/` (chỉ có `/` ở cuối) | Mọi thư mục tên `docs` ở bất kỳ đâu, mọi độ sâu |
| `/docs/*` | Chỉ tệp nằm trực tiếp trong `docs/` ở gốc, không vào thư mục con |
| `**/logs` | Thư mục hay tệp `logs` ở mọi độ sâu |
| `/.github/CODEOWNERS` | Đúng tệp đó |

Test cũng tự kiểm chính nó: khung trong `tests/fixtures/` phải bị bắt lỗi, và một CODEOWNERS đặt dòng `*` ở **cuối**
tệp (lỗi hay gặp nhất) phải bị bắt.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/advanced/01-olist-branching-release-strategy -q`
  pass. Test chỉ kiểm khung và CODEOWNERS; chất lượng chấm theo rubric trong
  `solutions/advanced/01-olist-branching-release-strategy/SOLUTION.md`.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi lựa chọn trong tài liệu gắn với một ràng buộc của đề (PCI, tách quyền, migration, app mobile) hoặc một chỉ số
  DORA, không phải "best practice" chung chung.

## Gợi ý

### Gợi ý 1

Bắt đầu từ câu hỏi: có bao nhiêu phiên bản Olist Shop đang chạy ở production? Một. Vậy nhánh release giữ để làm gì?
Ràng buộc "người duyệt khác người viết" không cần nhánh riêng: environment `production` có required reviewers trên
GitHub (hoặc protected environment trên GitLab) làm được điều đó cho chính artifact đã qua staging.

### Gợi ý 2

CODEOWNERS: dòng `*` đứng **đầu** tệp, các dòng cụ thể hơn đứng sau. Nếu có một dòng chung như `/services/`, nó phải
đứng trước `Dockerfile` và `/services/api/migrations/`, nếu không nó đè lên hai dòng đó. Tự kiểm bằng cách viết ra giấy: với mỗi đường dẫn trong bảng, đi từ dưới lên, dòng đầu tiên khớp
là owner. Đừng quên bảo vệ chính tệp CODEOWNERS và workflow CI: ai sửa được chúng là sửa được luật.
