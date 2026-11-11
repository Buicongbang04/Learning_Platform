---
title: Thiết kế repo GitOps nhiều môi trường và quy trình promote cho Olist Shop
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung tài liệu thiết kế, 7 phần
  - path: starter/repo/envs/staging/kustomization.yaml
    note: Overlay staging (cả thư mục repo)
  - path: starter/repo/envs/production/kustomization.yaml
    note: Overlay production
  - path: starter/repo/apps/root.yaml
    note: Application gốc (app-of-apps)
  - path: starter/repo/base/kustomization.yaml
    note: Base dùng chung, đã có sẵn
  - path: tests/test_multi_env.py
    note: Kiểm cấu trúc repo và tài liệu; không sửa
  - path: tests/fixtures/DESIGN.good.md
    note: Ví dụ đạt (hệ thống khác)
run:
  - uv run pytest tracks/devops/modules/12-gitops-secrets/exercises/advanced/01-multi-env-promotion -q -rs
---

## Mục tiêu

Thiết kế cách Olist Shop đi từ một commit tới staging rồi production bằng GitOps: repo chia thế nào, khác biệt giữa môi trường nằm ở đâu,
ai được promote, secret của mỗi môi trường mã hoá cho ai, lùi bằng cách nào. Viết đủ để một người mới vào team đọc là làm đúng.

## Đề bài

Olist Shop có hai môi trường: staging (namespace `olist-staging`, cluster `nonprod` dùng chung) và production (namespace `olist-production`,
cluster `prod` riêng). Một ArgoCD trên `nonprod` quản cả hai cluster. Release vài lần mỗi tuần; đợt sale 11.11 đóng băng thay đổi; mọi
thay đổi production phải có người duyệt thứ hai. CI (module 07) đã build và push image, biết digest của mỗi image.

**Phần 1, repo.** Hoàn thiện `starter/repo/` (base đã có sẵn):

| Chỗ | Yêu cầu |
| --- | --- |
| `envs/staging`, `envs/production` | Dùng chung `../../base`; `namespace` là `olist-staging`, `olist-production`; `images:` cho `devops-track/olist-shop` (promote là sửa đúng chỗ này); staging 1 replica api theo tag, production ít nhất 2 replica, ghim theo `digest: sha256:...` và có PodDisruptionBudget cho api (chỉ ở production) |
| `apps/` | Mỗi môi trường một Application trong namespace `argocd`, `path: envs/<môi trường>`, AppProject riêng mỗi môi trường (không `default`), staging sync tự động; mọi Application theo cùng nhánh `main` |
| `apps/root.yaml` | Application gốc (app-of-apps) trỏ `path: apps`, đích namespace `argocd` |

Repo URL là `https://git.example.com/olist/gitops.git`, cluster production tuỳ bạn đặt tên. Digest của production là ví dụ (64 ký tự
hex), không cần là image thật: bài này không deploy, chỉ render.

**Phần 2, tài liệu.** Điền `starter/DESIGN.md`, giữ đúng bảy tiêu đề `## 1.` tới `## 7.`. Rubric trong `SOLUTION.md` chấm nội dung.

**Cách test chấm** (không cần cluster; `kubectl kustomize` chạy trong sandbox).

| Phần | Test kiểm |
| --- | --- |
| Overlay | Mỗi overlay có `../../base` trong `resources`, render được, mọi object trong đúng namespace, có Deployment api |
| Image | Hai overlay có `images:` cho `devops-track/olist-shop`; image đã render không phải `latest` hay không tag; production có `digest` dạng `sha256:<64 hex>` |
| Production | api ≥ 2 replica ở production, đúng 1 ở staging; production có PodDisruptionBudget, staging không có |
| Application | Một Application cho mỗi `envs/<môi trường>`, đúng namespace đích, project riêng (hai project khác nhau, không `default`), `targetRevision` chỉ là `main` hay `HEAD`, staging có `automated` |
| App-of-apps | Đúng một Application trỏ `path: apps`, đích `argocd` |
| Tài liệu | Đủ `## 1.` tới `## 7.`, không còn `TODO`; phần 2 có khối code (cây thư mục), phần 3 có khối mermaid; số gạch đầu dòng tối thiểu: phần 3 bốn, phần 4 ba, phần 6 ba, phần 7 bốn |
| Từ khoá (không phân biệt hoa thường, một từ trong mỗi nhóm) | Phần 1: môi trường/environment; staging; production. Phần 2: base; overlay/envs/; app-of-apps/applicationset. Phần 3: pull request/PR; staging; digest/sha256; tự động/automated/bot/CI. Phần 4: AppProject; CODEOWNERS/branch protection/review. Phần 5: SOPS/External Secrets/Vault; recipient/khoá/key. Phần 6: revert; drift/self-heal. Phần 7: branch; Helm; ApplicationSet/Kargo/Flux |
| Bộ kiểm | Chạy trên ba fixture (khung, bản yếu, bản đạt của hệ thống khác) để chứng minh bắt được lỗi |

## Tiêu chí đạt

- Test pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10.
- Bảo vệ được thiết kế trước ba câu hỏi: "Sao không dùng nhánh `staging` và `production`?", "Image chạy trên production có chắc là image
  đã test trên staging không?", "Lúc 2 giờ sáng production hỏng, bạn lùi trong bao lâu và bằng lệnh gì?".

## Gợi ý

### Gợi ý 1

`kubectl kustomize repo/envs/production` để xem đúng thứ ArgoCD sẽ apply. Trong overlay, `images:` có `newTag` hay `digest`, `replicas:`
đổi số replica theo tên Deployment, `resources:` thêm tệp chỉ có ở môi trường đó.

### Gợi ý 2

Đọc `tests/fixtures/DESIGN.good.md` để thấy độ chi tiết mong đợi (hệ thống khác, đừng chép). Một thiết kế tốt nói rõ **ai** bấm nút ở mỗi
bước, **cái gì** tự động, và mỗi lựa chọn đã bỏ qua phương án nào vì sao.
