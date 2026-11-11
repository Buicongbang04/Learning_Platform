# Lời giải: repo GitOps nhiều môi trường và quy trình promote

`DESIGN.md` và `repo/` cạnh tệp này là **một** lời giải qua test; rubric dưới đây mới là thứ chấm nội dung.

## Hướng làm

**Repo.** Base giữ thứ giống nhau ở mọi nơi; overlay chỉ giữ khác biệt:

| | staging | production |
| --- | --- | --- |
| `namespace` | `olist-staging` | `olist-production` |
| Image | `newTag: 1.4.0-rc.2` (bot CI sửa) | `digest: sha256:...` (PR promote chép từ staging) |
| Replica api | 1 | 3, PDB `maxUnavailable: 1` |
| Cấu hình | `LOG_LEVEL=DEBUG` | `LOG_LEVEL=WARNING` |
| Application | auto sync, prune, self-heal | auto sync, self-heal, prune tay (`PruneLast`) |

Môi trường là **thư mục**, không là nhánh: mọi Application theo `main`. Promote là một PR nhỏ sửa đúng `images:` của overlay sau; review
thấy ngay cái gì đi lên production. App-of-apps (`apps/root.yaml`) quản ba Application; thêm môi trường là thêm một tệp.

**Tài liệu.** Bảy phần: bối cảnh có số liệu; cây thư mục và lý do; sơ đồ promote có cổng kiểm ở mỗi bước; quyền (AppProject, CODEOWNERS,
branch protection, ai có quyền ghi trên cluster); secret theo môi trường (creation_rule theo đường dẫn, recipient khác nhau); rollback bằng
`git revert` và xử lý drift; các đánh đổi đã cân nhắc.

## Quyết định cần cân nhắc

- **Thư mục hay nhánh cho môi trường.** Nhánh: merge kéo theo thay đổi chưa muốn promote, nhánh lệch nhau dần, khó trả lời "staging khác
  production chỗ nào". Thư mục: một `diff` hai overlay là đủ. Tài liệu của ArgoCD và bài "Stop using branches for deploying to different
  GitOps environments" của Codefresh đều khuyên thư mục.
- **Promote theo tag hay digest.** Tag có thể bị ghi đè; digest bất biến nên chắc chắn production chạy đúng byte đã test ở staging. Tag
  dễ đọc cho người; ghi cả hai (tag trong comment của PR, digest trong overlay) là cách phổ biến.
- **Ai sửa overlay.** Bot của CI sửa staging (PR tự merge khi CI xanh) hay Image Updater của Argo; production luôn qua PR có người duyệt.
  Công cụ như Kargo tự động hoá đường promote nhiều giai đoạn khi số môi trường lớn.
- **Một repo cho mọi app hay một repo mỗi team.** Repo chung dễ thấy toàn cảnh nhưng CODEOWNERS và quyền phức tạp; repo mỗi team gọn
  nhưng nền tảng chung (ingress, policy) cần chỗ riêng.
- **App-of-apps hay ApplicationSet.** ApplicationSet (generator theo thư mục, cluster, PR) bớt YAML lặp khi có nhiều đích, đổi lại template
  sai là hỏng mọi môi trường cùng lúc. Hai môi trường thì app-of-apps dễ đọc hơn.
- **Prune ở production.** Prune tự động gọn, nhưng một PR lỡ xoá Service là mất traffic ngay; `PruneLast`, review kỹ PR xoá, hay prune tay
  là các mức an toàn khác nhau.
- **Secret.** SOPS với recipient theo môi trường (dev không mở được secret production), hay External Secrets đọc secret manager của cloud
  khi cần xoay tự động.

## Rubric (10 điểm)

| Điểm | Tiêu chí |
| --- | --- |
| 1 | Bối cảnh có số liệu: môi trường, cluster, tần suất release, đóng băng, yêu cầu duyệt, ngoài phạm vi |
| 1 | Cấu trúc repo rõ: base, overlay theo môi trường, Application, app-of-apps hay ApplicationSet, có lý do |
| 1 | Môi trường là thư mục trên một nhánh, giải thích vì sao không dùng nhánh |
| 1 | Promote bất biến: build một lần, promote cùng digest, không build lại cho production |
| 1 | Mỗi bước promote có cổng kiểm rõ (CI, smoke, e2e, soak, người duyệt) và nói rõ bước nào tự động |
| 1 | Quyền: AppProject giới hạn namespace và cluster cho từng môi trường, CODEOWNERS và branch protection, quyền ghi trực tiếp trên cluster production |
| 1 | Secret theo môi trường: recipient hay khoá riêng, ai giải mã được gì, cách xoay |
| 1 | Rollback bằng `git revert` có ước lượng thời gian; đường khẩn cấp (tắt auto sync, rollback) và cách đưa Git về khớp |
| 1 | Drift: self-heal, alert OutOfSync, chính sách prune ở production |
| 1 | Đánh đổi thật: ít nhất bốn phương án bị bỏ qua, mỗi cái có lý do |

Trừ điểm: nhánh cho từng môi trường không giải thích được; tag `latest` hay tag trôi ở production; một AppProject cho mọi môi trường; secret
production giải mã được bằng khoá của staging; "rollback bằng `kubectl rollout undo`" mà không nói ArgoCD sẽ kéo về Git.

## Lab tay (không chấm tự động)

Trên một cluster kind riêng dùng một lần có ArgoCD bản đầy đủ (mục 0 của module), đẩy `repo/` lên một repo GitHub của bạn, tạo hai
namespace và ba AppProject, sửa `repoURL` rồi apply `apps/root.yaml`. Promote một tag từ staging sang production bằng một commit, rồi `git
revert` commit đó và đo thời gian tới khi production về bản cũ. Xoá cluster khi xong.
